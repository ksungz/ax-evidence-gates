"""Local answer-quality checks for KPS Decision Answer Gate."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


PLUGIN_VERSION = "0.1.0"

URL_RE = re.compile(r"https://[^\s\])>\"']+")
EVIDENCE_ID_RE = re.compile(r"\bE(?:1[0-4]|[1-9])\b")

SEVERITY_ORDER = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}

EVIDENCE_LIBRARY: dict[str, dict[str, str]] = {
    "E1": {
        "label": "카카오페이증권 회사소개",
        "url": "https://www.kakaopaysec.com/company/about/dynamicPage.do",
    },
    "E4": {
        "label": "개인정보 처리 위탁 문서의 고객센터/AI 상담 업무 공개 항목",
        "url": "https://www.kakaopaysec.com/policy-detail/policy-002/dynamicPage.do",
    },
    "E5": {
        "label": "카카오페이 기술블로그의 RAG와 보안 가드레일 사례",
        "url": "https://tech.kakaopay.com/post/choonsiri/",
    },
    "E6": {
        "label": "카카오페이증권 주문장애 안내",
        "url": "https://www.kakaopaysec.com/portal/cstmnotice-obstc/dynamicPage.do",
    },
    "E7": {
        "label": "카카오페이증권 해외주식 시세 안내",
        "url": "https://www.kakaopaysec.com/guide/quotation/dynamicPage.do",
    },
    "E8": {
        "label": "해외주식 거래설명서",
        "url": "https://www.kakaopaysec.com/downloadFile.do?id=10427",
    },
    "E9": {
        "label": "해외주식 소수점 거래설명서",
        "url": "https://www.kakaopaysec.com/downloadFile.do?id=10361",
    },
    "E13": {
        "label": "금융소비자보호법 제17조/제19조 공개 기준",
        "url": "https://www.law.go.kr/LSW//lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0017&lsiSeq=277247&urlMode=lsScJoRltInfoR",
    },
    "E14": {
        "label": "금융투자협회 광고/컴플라이언스 공개 기준",
        "url": "https://law.kofia.or.kr/service/law/lawFullScreen.do?historySeq=1757&seq=136",
    },
}


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    category: str
    message: str
    evidence_id: str
    evidence_url: str
    location: str
    suggestion: str
    matched_text: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    source: str
    case_type: str
    findings: list[Finding]


@dataclass(frozen=True)
class InputDocument:
    path: Path
    source: str
    content: str
    answer: str
    answer_start_line: int
    evidence_entries: list[dict[str, Any]]
    case_type: str
    payload: dict[str, Any] | None = None


UNSAFE_LANGUAGE_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        "direct_buy_or_sell",
        r"(?:지금|바로|오늘)\s*(?:사|사도|매수|매도)|(?:매수|매도|팔아|사야)\s*(?:하세요|해도\s*됩니다|해야\s*합니다)",
        "E13",
        "매수/매도 결론 대신 투자 목적, 기간, 보유 여부, 손실 감내 가능성 확인 질문으로 바꾸세요.",
    ),
    (
        "return_or_profit_guarantee",
        r"(?:수익|수익률|이익).{0,8}(?:보장|확실)|(?:확실히|반드시).{0,8}(?:오릅니다|수익|이익)",
        "E14",
        "수익이나 방향성을 단정하지 말고 불확실성과 손실 가능성을 함께 설명하세요.",
    ),
    (
        "loss_dismissal",
        r"(?:손해|손실).{0,10}(?:없|낮|걱정하지|안심)",
        "E8",
        "손실 가능성을 낮게 단정하지 말고 원금 손실 가능성과 투자자 책임을 분리해 안내하세요.",
    ),
    (
        "suitability_or_compliance_certified",
        r"(?:적합성|준법|규제\s*준수|법률\s*판단|컴플라이언스).{0,8}(?:완료|통과|보장|확인됨|문제없)",
        "E13",
        "이 도구는 사전 품질 점검만 수행한다고 표현하고 적합성/준법 완료처럼 보이는 표현을 제거하세요.",
    ),
    (
        "internal_system_claim",
        r"(?:내부\s*(?:시스템|API|데이터)|비공개\s*(?:API|데이터)|실시간\s*시세\s*API|계좌\s*정보|고객\s*데이터)",
        "E5",
        "샘플 fixture와 공개 근거 기반 검수라고 설명하고 내부 시스템/API 사용처럼 보이는 표현을 빼세요.",
    ),
]

NEGATION_HINTS = (
    "아닙",
    "없습니다",
    "수 없습니다",
    "하지 않습니다",
    "하지 않",
    "제공하지",
    "판단하지",
    "보장하지",
    "단정하지",
    "피해야",
    "금지",
)

INVESTMENT_CONTEXT_GROUPS: dict[str, tuple[str, ...]] = {
    "투자 목적": ("투자 목적", "목표", "왜 투자", "자금 용도"),
    "투자 기간": ("투자 기간", "보유 기간", "기간", "단기", "장기"),
    "보유 여부/주문 의도": ("보유", "주문 의도", "매수 의도", "매도 의도", "현재 보유"),
    "손실 감내 가능성": ("손실 감내", "위험 감수", "감내 가능", "손실을 감당"),
}

CASE_REQUIREMENTS: dict[str, list[dict[str, Any]]] = {
    "investment_decision": [
        {
            "id": "loss_risk",
            "label": "원금 손실 가능성",
            "keywords": ("원금 손실", "투자 손실", "예금자보호", "손실은 투자자"),
            "evidence_id": "E8",
            "severity": "high",
            "suggestion": "매수/매도 판단 전에 원금 손실 가능성과 투자 손실의 귀속을 명시하세요.",
        },
        {
            "id": "price_execution_uncertainty",
            "label": "시세/체결 불확실성",
            "keywords": ("시세", "체결", "지연", "가격 차이", "불리한 가격"),
            "evidence_id": "E7",
            "severity": "medium",
            "suggestion": "실시간 시세와 실제 체결 가격 차이, 지연 또는 오류 가능성을 확인 항목으로 넣으세요.",
        },
    ],
    "order_outage": [
        {
            "id": "emergency_order_channel",
            "label": "비상주문 채널",
            "keywords": ("비상주문", "고객센터", "ARS"),
            "evidence_id": "E6",
            "severity": "medium",
            "suggestion": "주문장애 문의에는 공개 안내의 비상주문 채널 확인을 포함하세요.",
        },
        {
            "id": "outage_evidence_capture",
            "label": "증빙자료 준비",
            "keywords": ("증빙", "캡처", "동영상", "화면"),
            "evidence_id": "E6",
            "severity": "medium",
            "suggestion": "장애 화면 캡처나 동영상 등 증빙자료 준비 안내를 추가하세요.",
        },
        {
            "id": "compensation_limits",
            "label": "보상 제외 가능성",
            "keywords": ("보상 제외", "단순 시세지연", "체결지연", "유관기관"),
            "evidence_id": "E6",
            "severity": "medium",
            "suggestion": "단순 시세지연, 체결지연, 유관기관 장애 등 보상 제외 가능성을 단정 없이 안내하세요.",
        },
    ],
    "market_data_delay": [
        {
            "id": "realtime_vs_execution_price",
            "label": "실시간 시세와 실제 시세 차이",
            "keywords": ("실시간 시세", "실제 시세", "체결 가격", "가격 차이"),
            "evidence_id": "E7",
            "severity": "medium",
            "suggestion": "앱 표시 가격과 실제 시세/체결 가격이 다를 수 있음을 설명하세요.",
        },
        {
            "id": "delayed_quote_switch",
            "label": "지연 시세 전환 가능성",
            "keywords": ("지연", "15분", "전환", "데이터 제공자", "거래소", "현지 중개사"),
            "evidence_id": "E7",
            "severity": "medium",
            "suggestion": "시세 제공이 원활하지 않을 때 지연 데이터로 전환될 수 있음을 안내하세요.",
        },
    ],
    "fractional_order": [
        {
            "id": "best_price_no_limit",
            "label": "최적가 실행과 가격 지정 제한",
            "keywords": ("최적가", "가격 지정", "지정가", "불리한 가격"),
            "evidence_id": "E9",
            "severity": "medium",
            "suggestion": "소수점 주문은 가격 지정이 제한되고 불리한 가격에 체결될 수 있음을 설명하세요.",
        },
        {
            "id": "correction_cancel_limits",
            "label": "정정/취소 제한",
            "keywords": ("정정", "취소", "제한"),
            "evidence_id": "E9",
            "severity": "medium",
            "suggestion": "소수점 주문의 정정/취소 제한 가능성을 답변에 포함하세요.",
        },
        {
            "id": "rights_limits",
            "label": "권리행사 제한",
            "keywords": ("권리행사", "의결권", "배당", "권리"),
            "evidence_id": "E9",
            "severity": "low",
            "suggestion": "소수점 보유분의 권리행사 제한 가능성을 필요한 경우 확인 항목으로 안내하세요.",
        },
    ],
}


def evaluate_path(raw_path: str | Path) -> list[EvaluationResult]:
    path = Path(raw_path)
    if path.is_dir():
        results: list[EvaluationResult] = []
        for child in sorted(path.iterdir()):
            if child.suffix.lower() in {".md", ".json"}:
                results.append(evaluate_file(child))
        return results
    return [evaluate_file(path)]


def evaluate_file(raw_path: str | Path) -> EvaluationResult:
    document = load_document(Path(raw_path))
    return evaluate_document(document)


def evaluate_text(
    content: str,
    *,
    case_type: str | None = None,
    source: str = "<memory>",
) -> EvaluationResult:
    """Evaluate an in-memory Markdown draft without writing a temporary file."""
    answer, answer_start_line = extract_markdown_answer(content)
    resolved_case_type = case_type or infer_case_type(Path(source), content, None)
    document = InputDocument(
        path=Path(source),
        source=source,
        content=content,
        answer=answer,
        answer_start_line=answer_start_line,
        evidence_entries=[],
        case_type=resolved_case_type,
    )
    return evaluate_document(document)


def evaluate_document(document: InputDocument) -> EvaluationResult:
    findings: list[Finding] = []
    findings.extend(check_unsafe_language(document))
    findings.extend(check_evidence_urls(document))
    findings.extend(check_user_context(document))
    findings.extend(check_case_requirements(document))
    return EvaluationResult(
        source=document.source,
        case_type=document.case_type,
        findings=sorted(findings, key=lambda item: (-SEVERITY_ORDER[item.severity], item.id)),
    )


def load_document(path: Path) -> InputDocument:
    content = path.read_text(encoding="utf-8")
    payload: dict[str, Any] | None = None
    answer = content
    answer_start_line = 1
    evidence_entries: list[dict[str, Any]] = []

    if path.suffix.lower() == ".json":
        loaded = json.loads(content)
        if not isinstance(loaded, dict):
            raise ValueError(f"{path} must contain a JSON object")
        payload = loaded
        answer = extract_answer_text(loaded)
        evidence_entries = extract_evidence_entries(loaded)
    elif path.suffix.lower() == ".md":
        answer, answer_start_line = extract_markdown_answer(content)

    case_type = infer_case_type(path, content, payload)
    return InputDocument(
        path=path,
        source=str(path),
        content=content,
        answer=answer,
        answer_start_line=answer_start_line,
        evidence_entries=evidence_entries,
        case_type=case_type,
        payload=payload,
    )


def extract_markdown_answer(content: str) -> tuple[str, int]:
    lines = content.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if re.match(r"^#{2,6}\s*답변\s*초안\s*$", line.strip()):
            start_index = index + 1
            break

    if start_index is None:
        return content, 1

    end_index = len(lines)
    for index in range(start_index, len(lines)):
        if re.match(r"^#{1,6}\s+", lines[index]):
            end_index = index
            break

    answer_lines = lines[start_index:end_index]
    return "\n".join(answer_lines).strip(), start_index + 1


def extract_answer_text(payload: dict[str, Any]) -> str:
    preferred_keys = ("answer", "draft_answer", "response", "content", "body")
    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return "\n".join(iter_string_values(payload))


def extract_evidence_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("evidence", "evidences", "sources", "references"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def iter_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_string_values(child)


def infer_case_type(path: Path, content: str, payload: dict[str, Any] | None) -> str:
    if payload and isinstance(payload.get("case_type"), str):
        return str(payload["case_type"])

    if path.name in {"bad-answer.md", "better-answer.md"} or "investment" in path.name:
        return "investment_decision"

    haystack = f"{path.name}\n{content}"
    if re.search(r"주문장애|비상주문|매도하지\s*못|앱이\s*안", haystack):
        return "order_outage"
    if re.search(r"시세|체결\s*가격|가격이\s*다르|지연", haystack):
        return "market_data_delay"
    if re.search(r"소수점|정정|취소|가격\s*지정", haystack):
        return "fractional_order"
    return "investment_decision"


def check_unsafe_language(document: InputDocument) -> list[Finding]:
    findings: list[Finding] = []
    for rule_id, pattern, evidence_id, suggestion in UNSAFE_LANGUAGE_PATTERNS:
        for match in re.finditer(pattern, document.answer, flags=re.IGNORECASE):
            if is_negated(document.answer, match.start(), match.end()):
                continue
            findings.append(
                make_finding(
                    finding_id=f"unsafe_language.{rule_id}.{line_number(document.answer, match.start())}",
                    severity="high",
                    category="unsafe_investment_language",
                    message="투자 추천, 수익 보장, 준법 완료, 내부 시스템 사용처럼 오해될 수 있는 표현이 있습니다.",
                    evidence_id=evidence_id,
                    location=location_for_offset(document, match.start()),
                    suggestion=suggestion,
                    matched_text=match.group(0),
                )
            )
    return findings


def check_evidence_urls(document: InputDocument) -> list[Finding]:
    findings: list[Finding] = []
    all_urls = extract_urls(document.content)

    for index, entry in enumerate(document.evidence_entries):
        evidence_id = str(entry.get("id") or entry.get("evidence_id") or "E1")
        raw_url = entry.get("url") or entry.get("evidence_url")
        if not isinstance(raw_url, str) or not raw_url.startswith("https://"):
            findings.append(
                make_finding(
                    finding_id=f"evidence_url_missing.entry_{index}",
                    severity="high",
                    category="evidence_url_missing",
                    message="JSON evidence entry에 공개 근거 URL이 없습니다.",
                    evidence_id=normalize_evidence_id(evidence_id),
                    location=f"{document.source}:evidence[{index}]",
                    suggestion="각 evidence entry에 검증 가능한 https 공개 URL을 넣으세요.",
                    matched_text=json.dumps(entry, ensure_ascii=False),
                )
            )
        else:
            all_urls.append(raw_url)

    evidence_lines = [
        (line_index, line)
        for line_index, line in enumerate(document.content.splitlines(), start=1)
        if re.search(r"근거|출처|evidence|reference", line, flags=re.IGNORECASE)
    ]
    for line_index, line in evidence_lines:
        ids = EVIDENCE_ID_RE.findall(line)
        if ids and not extract_urls(line):
            findings.append(
                make_finding(
                    finding_id=f"evidence_url_missing.line_{line_index}",
                    severity="high",
                    category="evidence_url_missing",
                    message="근거 ID는 있지만 같은 근거 항목에 공개 URL이 없습니다.",
                    evidence_id=ids[0],
                    location=f"{document.source}:line {line_index}",
                    suggestion="근거 ID만 쓰지 말고 공식 문서의 공개 URL을 함께 적으세요.",
                    matched_text=line.strip(),
                )
            )

    if not all_urls:
        expected_id = expected_evidence_for_case(document.case_type)
        findings.append(
            make_finding(
                finding_id="evidence_url_missing.document",
                severity="high",
                category="evidence_url_missing",
                message="답변 초안 전체에서 공개 근거 URL을 찾지 못했습니다.",
                evidence_id=expected_id,
                location=f"{document.source}:document",
                suggestion="답변 하단이나 JSON evidence 필드에 관련 공식 문서 URL을 최소 1개 이상 넣으세요.",
            )
        )

    return findings


def check_user_context(document: InputDocument) -> list[Finding]:
    if document.case_type != "investment_decision":
        return []

    missing = [
        label
        for label, keywords in INVESTMENT_CONTEXT_GROUPS.items()
        if not contains_any(document.answer, keywords)
    ]
    if not missing:
        return []

    return [
        make_finding(
            finding_id="missing_user_context.investment_decision",
            severity="medium",
            category="missing_user_context",
            message=f"투자 판단 전 확인해야 할 사용자 조건이 부족합니다: {', '.join(missing)}.",
            evidence_id="E13",
            location=f"{document.source}:document",
            suggestion="투자 목적, 기간, 보유 여부/주문 의도, 손실 감내 가능성을 확인 질문으로 분리하세요.",
        )
    ]


def check_case_requirements(document: InputDocument) -> list[Finding]:
    requirements = CASE_REQUIREMENTS.get(document.case_type, [])
    findings: list[Finding] = []
    for requirement in requirements:
        if contains_any(document.answer, requirement["keywords"]):
            continue
        findings.append(
            make_finding(
                finding_id=f"missing_risk_or_limit.{document.case_type}.{requirement['id']}",
                severity=requirement["severity"],
                category="missing_risk_or_limit",
                message=f"{requirement['label']} 설명이 부족합니다.",
                evidence_id=requirement["evidence_id"],
                location=f"{document.source}:document",
                suggestion=requirement["suggestion"],
            )
        )
    return findings


def make_finding(
    *,
    finding_id: str,
    severity: str,
    category: str,
    message: str,
    evidence_id: str,
    location: str,
    suggestion: str,
    matched_text: str | None = None,
) -> Finding:
    normalized_id = normalize_evidence_id(evidence_id)
    evidence = EVIDENCE_LIBRARY[normalized_id]
    return Finding(
        id=finding_id,
        severity=severity,
        category=category,
        message=message,
        evidence_id=normalized_id,
        evidence_url=evidence["url"],
        location=location,
        suggestion=suggestion,
        matched_text=matched_text,
    )


def normalize_evidence_id(raw_evidence_id: str) -> str:
    if raw_evidence_id in EVIDENCE_LIBRARY:
        return raw_evidence_id
    return expected_evidence_for_case("investment_decision")


def expected_evidence_for_case(case_type: str) -> str:
    return {
        "order_outage": "E6",
        "market_data_delay": "E7",
        "fractional_order": "E9",
        "investment_decision": "E8",
    }.get(case_type, "E8")


def contains_any(text: str, keywords: Iterable[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def extract_urls(text: str) -> list[str]:
    return [match.group(0).rstrip(".,") for match in URL_RE.finditer(text)]


def is_negated(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 24) : min(len(text), end + 24)]
    return any(hint in window for hint in NEGATION_HINTS)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def location_for_offset(document: InputDocument, offset: int) -> str:
    return f"{document.source}:line {document.answer_start_line + line_number(document.answer, offset) - 1}"


def summarize(results: list[EvaluationResult]) -> dict[str, Any]:
    severity_counts = {severity: 0 for severity in SEVERITY_ORDER}
    for result in results:
        for finding in result.findings:
            severity_counts[finding.severity] += 1
    return {
        "files_checked": len(results),
        "findings": sum(severity_counts.values()),
        "severity_counts": severity_counts,
    }


def render_json(results: list[EvaluationResult]) -> str:
    payload = {
        "tool": "kps-decision-answer-gate",
        "version": PLUGIN_VERSION,
        "summary": summarize(results),
        "results": [
            {
                "source": result.source,
                "case_type": result.case_type,
                "findings": [asdict(finding) for finding in result.findings],
            }
            for result in results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_markdown(results: list[EvaluationResult]) -> str:
    summary = summarize(results)
    lines = [
        "# KPS Decision Answer Gate Report",
        "",
        f"- Files checked: {summary['files_checked']}",
        f"- Findings: {summary['findings']}",
        "- Severity counts: "
        + ", ".join(
            f"{severity}={summary['severity_counts'][severity]}"
            for severity in ("high", "medium", "low", "info")
        ),
        "",
    ]

    for result in results:
        lines.extend([f"## {result.source}", "", f"- Case type: {result.case_type}"])
        if not result.findings:
            lines.extend(["- Result: no findings", ""])
            continue
        lines.append("")
        for finding in result.findings:
            lines.extend(
                [
                    f"### {finding.id}",
                    "",
                    f"- Severity: {finding.severity}",
                    f"- Category: {finding.category}",
                    f"- Message: {finding.message}",
                    f"- Evidence: {finding.evidence_id} {finding.evidence_url}",
                    f"- Location: {finding.location}",
                    f"- Suggestion: {finding.suggestion}",
                ]
            )
            if finding.matched_text:
                lines.append(f"- Matched text: `{finding.matched_text}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def has_findings_at_or_above(results: list[EvaluationResult], severity: str) -> bool:
    threshold = SEVERITY_ORDER[severity]
    return any(SEVERITY_ORDER[finding.severity] >= threshold for result in results for finding in result.findings)

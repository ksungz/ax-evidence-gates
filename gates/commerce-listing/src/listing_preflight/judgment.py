"""Evidence-limited Codex judgment helpers.

The SKILL.md is the source of truth for how Codex should reason. These helpers
make the five local examples reproducible without calling a remote model.
"""

from __future__ import annotations

from .rules import make_finding


def run_judgment_hints(data):
    findings = []
    text = _combined_text(data)
    attributes = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
    components = attributes.get("components") if isinstance(attributes.get("components"), dict) else {}
    tags = data.get("tags") if isinstance(data.get("tags"), list) else []

    if _contains_any(text, ["푸퍼 자켓", "패딩 점퍼", "패딩"]) and not _component_or_tag_has(
        components, tags, ["푸퍼 자켓", "패딩 점퍼", "패딩"]
    ):
        findings.append(
            make_finding(
                rule_id="TERM-CLUSTER-PUFFER",
                severity="warning",
                title="푸퍼 자켓/패딩/패딩 점퍼 클러스터 제안",
                input_location="/product_name",
                input_quote=data.get("product_name", ""),
                evidence_key="taxonomy_terms",
                suggestion_action="review",
                suggestion_description="표준형을 단정하지 않고 상품 유형 속성이나 태그에 동의어 클러스터 후보를 남긴다.",
                diff=_diff_add_component(
                    "attributes.components.item_type",
                    "푸퍼 자켓 | 패딩 | 패딩 점퍼 클러스터",
                ),
            )
        )

    if _contains_any(text, ["크롭", "숏"]) and not components.get("length"):
        findings.append(
            make_finding(
                rule_id="ATTR-GAP-LENGTH",
                severity="warning",
                title="기장 표현은 있으나 속성 기장값 없음",
                input_location="/attributes/components/length",
                input_quote=_first_term(text, ["크롭", "숏"]),
                evidence_key="taxonomy_terms",
                suggestion_action="add",
                suggestion_description="크롭/숏은 공개 문서화된 표현 차이 그룹이므로 기장 속성 후보로 검토한다.",
                diff=_diff_add_component("attributes.components.length", "크롭 | 숏 클러스터 후보"),
            )
        )

    if _contains_any(text, ["퍼널넥", "하이넥", "U넥", "라운드넥"]) and not components.get("neckline"):
        findings.append(
            make_finding(
                rule_id="ATTR-GAP-NECKLINE",
                severity="warning",
                title="넥라인 표현은 있으나 속성 넥라인값 없음",
                input_location="/attributes/components/neckline",
                input_quote=_first_term(text, ["퍼널넥", "하이넥", "U넥", "라운드넥"]),
                evidence_key="taxonomy_terms",
                suggestion_action="add",
                suggestion_description="퍼널넥/하이넥 또는 U넥/라운드넥은 공개 문서화된 사례이므로 넥라인 속성 후보로 검토한다.",
                diff=_diff_add_component("attributes.components.neckline", "넥라인 클러스터 후보"),
            )
        )

    if "U넥" in text and "라운드넥" in text:
        findings.append(
            make_finding(
                rule_id="TERM-MIXED-NECKLINE",
                severity="warning",
                title="U넥/라운드넥 혼재",
                input_location="/product_name,/description,/tags,/attributes",
                input_quote="U넥 + 라운드넥",
                evidence_key="taxonomy_terms",
                suggestion_action="review",
                suggestion_description="표준형을 단정하지 않고 같은 넥라인 클러스터인지 검토한다.",
                diff=_diff_add_component("attributes.components.neckline_review", "U넥/라운드넥 혼재 검토"),
            )
        )

    if "미디" in text:
        findings.append(
            make_finding(
                rule_id="TERM-MIDI-MEASUREMENT-REQUEST",
                severity="warning",
                title="'미디' 기장 모호어 실측 확인 필요",
                input_location="/product_name,/description",
                input_quote="미디",
                evidence_key="taxonomy_terms",
                suggestion_action="review",
                suggestion_description="'미디'는 용어 치환이 아니라 실측 수치 확인 요청으로만 처리한다.",
                diff=_diff_add_component("size_chart", "기장 실측 수치 확인"),
            )
        )

    category = data.get("category") if isinstance(data.get("category"), dict) else {}
    is_hood_item = _contains_any(text + " " + category.get("sub", ""), ["후드티셔츠", "후드 티셔츠", "후드", "후디"])
    if is_hood_item and any(tag == "스웨트셔츠" for tag in tags):
        findings.append(
            make_finding(
                rule_id="TAG-MISMATCH-SWEATSHIRT",
                severity="warning",
                title="후드티셔츠 상품의 스웨트셔츠 태그 오입력 의심",
                input_location="/tags",
                input_quote="스웨트셔츠",
                evidence_key="taxonomy_terms",
                suggestion_action="replace",
                suggestion_description="후드티셔츠/후드/후디/로고티 표현 변형은 제안만 하고, 스웨트셔츠 태그는 공개 오입력 사례로 검토한다.",
                diff="--- original\n+++ suggested\n@@\n- tags: 스웨트셔츠\n+ tags: 후드티셔츠 또는 후드 관련 태그 후보",
            )
        )

    return findings


def _combined_text(data):
    parts = []
    for key in ["product_name", "description"]:
        if isinstance(data.get(key), str):
            parts.append(data[key])
    if isinstance(data.get("tags"), list):
        parts.extend(tag for tag in data["tags"] if isinstance(tag, str))
    if isinstance(data.get("attributes"), dict):
        for group in data["attributes"].values():
            if isinstance(group, dict):
                parts.extend(value for value in group.values() if isinstance(value, str))
    return " ".join(parts)


def _contains_any(text, terms):
    return any(term in text for term in terms)


def _component_or_tag_has(components, tags, terms):
    component_values = " ".join(value for value in components.values() if isinstance(value, str))
    tag_values = " ".join(tag for tag in tags if isinstance(tag, str))
    combined = f"{component_values} {tag_values}"
    return _contains_any(combined, terms)


def _first_term(text, terms):
    for term in terms:
        if term in text:
            return term
    return ""


def _diff_add_component(path, value):
    return f"--- original\n+++ suggested\n@@\n- {path}: <missing>\n+ {path}: {value}"

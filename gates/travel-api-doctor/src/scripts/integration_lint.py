#!/usr/bin/env python3
"""마이리얼트립 Open API 통합 코드 린터.

개발자센터(docs.myrealtrip.com)가 스스로 문서화한 통합 함정만 검사한다.
규칙 본문과 문서 원문 인용은 rules/pitfalls.json에 있다.

정적 휴리스틱 검사다. 미검출(false negative)과 오검출(false positive)이
있을 수 있으며, 각 발견 항목은 문서 원문 인용과 함께 보고되므로
개발자가 근거를 직접 확인할 수 있다.

사용법:
    python3 scripts/integration_lint.py <파일|디렉터리>... [--format json|korean-summary]

종료 코드: error 발견 시 1, 그 외 0.
"""

import argparse
import json
import re
import sys
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "pitfalls.json"
SOURCE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

# 다공항 도시코드 중 문서 예시(SEL)와 흔히 혼동되는 대표 코드만 보수적으로 검사한다.
CITY_CODES = ("SEL", "TYO", "OSA", "PAR", "LON", "NYC", "BJS", "SHA")

MRT_PATH_HINTS = ("/v1/products/", "/v1/mylink", "/v1/reservations", "/v1/revenues")


def load_rules():
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return {r["id"]: r for r in data["rules"]}, data["source"]


def line_of(content, match_start):
    return content.count("\n", 0, match_start) + 1


def check_file(path, content, rules):
    findings = []

    def add(rule_id, line):
        rule = rules[rule_id]
        findings.append({
            "rule": rule_id,
            "severity": rule["severity"],
            "file": str(path),
            "line": line,
            "title": rule["title"],
            "fix": rule["fix"],
            "docQuote": rule["docQuote"],
        })

    has_tna = bool(re.search(r"/v1/products/tna|searchTnas", content))
    has_stay_flight = bool(re.search(r"/v1/products/(accommodation|flight)", content))
    has_mylink = "/v1/mylink" in content
    has_reservations = "/v1/reservations" in content
    touches_mrt = any(h in content for h in MRT_PATH_HINTS)

    # R1: 투어 검색에 page=0
    if has_tna:
        m = re.search(r"""["']?page["']?\s*[:=]\s*0\b""", content)
        if m:
            add("tna-pagination-zero-based", line_of(content, m.start()))

    # R2: 투어 응답에서 페이지 크기를 size로 읽는 의심 (perPage 미사용 시에만)
    if has_tna and "perPage" not in content:
        m = re.search(r"""["']size["']|\.size\b""", content)
        if m:
            add("tna-pagination-field-mixup", line_of(content, m.start()))

    # R2 역방향: 숙소/항공 응답에서 perPage 참조
    if has_stay_flight and not has_tna and "perPage" in content:
        m = re.search(r"perPage", content)
        add("tna-pagination-field-mixup", line_of(content, m.start()))

    # R3: fromCityCode/toCityCode에 도시코드 리터럴
    m = re.search(
        r"""(?:from|to)CityCode["']?\s*[:=]\s*["'](%s)["']""" % "|".join(CITY_CODES),
        content,
    )
    if m:
        add("airport-code-trap", line_of(content, m.start()))

    # R4: mylink 사용 + 길이 검증 부재
    if has_mylink and not re.search(r"2,?000|len\s*\(|\.length\b", content):
        m = re.search(r"/v1/mylink", content)
        add("mylink-length-unchecked", line_of(content, m.start()))

    # R5: pageSize > 300
    for m in re.finditer(r"""pageSize["']?\s*[:=]\s*(\d+)""", content):
        if int(m.group(1)) > 300:
            add("reservations-pagesize-over-300", line_of(content, m.start()))

    # R6: MRT API 사용 + 429/재시도 처리 부재
    if touches_mrt and not re.search(r"429|retry|backoff", content, re.IGNORECASE):
        add("missing-429-retry", 1)

    # R7: Authorization 값에 Bearer 접두사 누락
    for m in re.finditer(
        r"""["']Authorization["']\s*[:=]\s*(f?["'][^"']*["']|[A-Za-z_][A-Za-z0-9_.]*)""",
        content,
    ):
        value = m.group(1)
        quoted = re.match(r"""f?["'](.*)["']$""", value)
        if quoted:
            if not quoted.group(1).startswith("Bearer "):
                add("bearer-prefix-missing", line_of(content, m.start()))
        elif "Bearer" not in content:
            # 변수 대입인데 파일 어디에도 Bearer 접두사 조합이 없다.
            add("bearer-prefix-missing", line_of(content, m.start()))

    # R8: API 키 하드코딩 의심
    m = re.search(
        r"""(?:api[_-]?key|API_KEY|apiKey)\s*[:=]\s*["'][A-Za-z0-9_\-]{24,}["']""",
        content,
    )
    if m:
        add("hardcoded-api-key", line_of(content, m.start()))

    # R9: 예약 내역 조회기간 안내 (정적으로 판정 불가 → info)
    if has_reservations:
        m = re.search(r"/v1/reservations", content)
        add("reservations-lookback-window", line_of(content, m.start()))

    # R10: 상세/옵션/캘린더 간헐적 빈 결과 안내
    m = re.search(r"/v1/products/tna/(detail|options|calendars)|getTna(Detail|Options)", content)
    if m:
        add("tna-intermittent-empty", line_of(content, m.start()))

    return findings


def collect_files(targets):
    files = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files.extend(
                f for f in sorted(p.rglob("*")) if f.suffix in SOURCE_EXTS and f.is_file()
            )
        elif p.is_file():
            files.append(p)
        else:
            print(f"경로를 찾을 수 없습니다: {t}", file=sys.stderr)
            sys.exit(2)
    return files


SEVERITY_KO = {"error": "오류", "warn": "경고", "info": "참고"}


def korean_summary(findings, file_count, source):
    counts = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        counts[f["severity"]] += 1
    lines = [
        f"검사 파일: {file_count}개",
        f"오류 {counts['error']}건 / 경고 {counts['warn']}건 / 참고 {counts['info']}건",
        "",
    ]
    order = {"error": 0, "warn": 1, "info": 2}
    for f in sorted(findings, key=lambda x: (order[x["severity"]], x["file"], x["line"])):
        lines.append(
            f"[{SEVERITY_KO[f['severity']]}] {f['file']}:{f['line']} — {f['title']}"
        )
        lines.append(f"  조치: {f['fix']}")
        lines.append(f"  근거: \"{f['docQuote']}\"")
        lines.append("")
    lines.append(f"근거 출처: {source}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="검사할 파일 또는 디렉터리")
    parser.add_argument(
        "--format", choices=["json", "korean-summary"], default="korean-summary"
    )
    args = parser.parse_args(argv)

    rules, source = load_rules()
    files = collect_files(args.targets)
    findings = []
    for f in files:
        findings.extend(check_file(f, f.read_text(encoding="utf-8"), rules))

    if args.format == "json":
        print(json.dumps({"files": len(files), "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print(korean_summary(findings, len(files), source))

    return 1 if any(f["severity"] == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())

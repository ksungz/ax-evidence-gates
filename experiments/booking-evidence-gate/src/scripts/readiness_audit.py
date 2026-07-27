#!/usr/bin/env python3
"""Audit MyRealTrip TNA booking claims against documented field evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORTED = "SUPPORTED"
CONDITIONAL = "CONDITIONAL"
BLOCKED = "BLOCKED"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RELATIVE_DATE_RE = re.compile(r"(오늘|내일|모레|이번\s*주|다음\s*주|이번\s*달|다음\s*달)")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def decode_pointer_part(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def resolve_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer}")
    current = document
    for raw_part in pointer.strip("/").split("/"):
        part = decode_pointer_part(raw_part)
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(pointer)
    return current


def pointer_matches(pattern: str, path: str) -> bool:
    if "*" in pattern:
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return False
        return all(expected == "*" or expected == actual for expected, actual in zip(pattern_parts, path_parts))
    return path == pattern or path.startswith(pattern.rstrip("/") + "/")


def has_evidence(claim: dict[str, Any], pattern: str) -> bool:
    return any(pointer_matches(pattern, item.get("path", "")) for item in claim.get("evidence", []))


def find_case(evidence: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    cases = evidence.get("cases", [])
    if not cases:
        raise ValueError("Evidence fixture has no cases")
    case_id = claim.get("caseId")
    if case_id:
        for case in cases:
            if case.get("caseId") == case_id:
                return case
        raise KeyError(f"Unknown caseId: {case_id}")
    return cases[0]


def collect_evidence_values(case: dict[str, Any], claim: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    resolved = []
    missing = []
    for item in claim.get("evidence", []):
        path = item.get("path")
        if not path:
            missing.append("<empty evidence path>")
            continue
        try:
            resolved.append({"path": path, "value": resolve_pointer(case, path)})
        except (KeyError, IndexError, ValueError) as exc:
            missing.append(f"{path} ({exc.__class__.__name__})")
    return resolved, missing


def get_nested(document: dict[str, Any], pointer: str, default: Any = None) -> Any:
    try:
        return resolve_pointer(document, pointer)
    except (KeyError, IndexError, ValueError):
        return default


def selected_date_is_blocked(case: dict[str, Any], selected_date: str) -> bool:
    block_dates = get_nested(case, "/tnaCalendars/response/data/blockDates", [])
    return isinstance(block_dates, list) and selected_date in block_dates


def options_for_case(case: dict[str, Any]) -> list[dict[str, Any]]:
    options = get_nested(case, "/tnaOptions/response/data/options", [])
    return options if isinstance(options, list) else []


def audit_availability(answer: dict[str, Any], case: dict[str, Any], claim: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    selected_date = claim.get("selectedDate")
    if not isinstance(selected_date, str) or not DATE_RE.match(selected_date):
        reasons.append("availability claim needs selectedDate in YYYY-MM-DD")
    if RELATIVE_DATE_RE.search(claim.get("span", "")) and not answer.get("currentDate"):
        reasons.append("relative date wording needs currentDate")

    option_date = get_nested(case, "/tnaOptions/response/data/selectedDate")
    if option_date != selected_date:
        reasons.append("tnaOptions selectedDate does not match claim selectedDate")

    if not options_for_case(case):
        reasons.append("tnaOptions options is empty or missing")

    quantity = claim.get("quantity")
    option_id = claim.get("optionId")
    if quantity is not None:
        matching_options = options_for_case(case)
        if option_id is not None:
            matching_options = [option for option in matching_options if option.get("id") == option_id]
            if not matching_options:
                reasons.append("optionId not found in options")
        if not isinstance(quantity, int) or quantity <= 0:
            reasons.append("quantity must be a positive integer")
        else:
            for option in matching_options:
                min_quantity = option.get("minPurchaseQuantity")
                available_quantity = option.get("availablePurchaseQuantity")
                if isinstance(min_quantity, int) and quantity < min_quantity:
                    reasons.append("quantity is below options[].minPurchaseQuantity")
                if isinstance(available_quantity, int) and quantity > available_quantity:
                    reasons.append("quantity exceeds options[].availablePurchaseQuantity")

    if selected_date and selected_date_is_blocked(case, selected_date):
        reasons.append("tnaCalendars blockDates contains selectedDate")

    if not has_evidence(claim, "/tnaOptions/response/data/selectedDate"):
        reasons.append("missing evidence path for tnaOptions selectedDate")
    if not has_evidence(claim, "/tnaOptions/response/data/options"):
        reasons.append("missing evidence path for tnaOptions options")

    return (BLOCKED if reasons else SUPPORTED), reasons


def audit_instant_confirm(case: dict[str, Any], claim: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    if get_nested(case, "/tnaCalendars/response/data/instantConfirm") is not True:
        reasons.append("tnaCalendars instantConfirm is not true")
    if not has_evidence(claim, "/tnaCalendars/response/data/instantConfirm"):
        reasons.append("missing evidence path for instantConfirm")
    return (BLOCKED if reasons else SUPPORTED), reasons


def audit_option_price(case: dict[str, Any], claim: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    if not has_evidence(claim, "/tnaOptions/response/data/options/*/salePrice"):
        reasons.append("option price claims need options[].salePrice evidence")
    if not has_evidence(claim, "/tnaOptions/response/data/options/*/currency"):
        reasons.append("option price claims need options[].currency evidence")
    if any(item.get("path", "").startswith("/tnaSearch/response/data/items/") for item in claim.get("evidence", [])):
        reasons.append("search items[].salePrice is only starting-price evidence, not final option price")
    if any(item.get("path", "").startswith("/tnaCalendars/response/data/basePrice") for item in claim.get("evidence", [])):
        reasons.append("calendar basePrice is display-only starting-price evidence and must not be parsed")

    options = options_for_case(case)
    option_id = claim.get("optionId")
    amount = claim.get("amount")
    currency = claim.get("currency")
    selected_options = options
    if option_id is not None:
        selected_options = [option for option in options if option.get("id") == option_id]
        if not selected_options:
            reasons.append("optionId not found in options")
    if amount is not None and not any(option.get("salePrice") == amount for option in selected_options):
        reasons.append("claimed amount does not match options[].salePrice")
    if currency is not None and not any(option.get("currency") == currency for option in selected_options):
        reasons.append("claimed currency does not match options[].currency")

    return (BLOCKED if reasons else SUPPORTED), reasons


def audit_search_starting_price(case: dict[str, Any], claim: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    if not (
        has_evidence(claim, "/tnaSearch/response/data/items/*/salePrice")
        or has_evidence(claim, "/tnaSearch/response/data/items/*/priceDisplay")
    ):
        reasons.append("starting price claims need search salePrice or priceDisplay evidence")
    if re.search(r"(최종|결제|총액)", claim.get("span", "")):
        reasons.append("starting-price evidence must not be worded as final payment price")
    return (BLOCKED if reasons else SUPPORTED), reasons


def audit_list_value(case: dict[str, Any], claim: dict[str, Any], field: str) -> tuple[str, list[str]]:
    reasons = []
    pattern = f"/tnaDetail/response/data/{field}"
    values = get_nested(case, pattern, [])
    claimed_value = claim.get("value")
    if not has_evidence(claim, pattern):
        reasons.append(f"missing evidence path for {field}")
    if claimed_value is not None and claimed_value not in values:
        reasons.append(f"claimed value is not present in {field}")
    return (BLOCKED if reasons else SUPPORTED), reasons


def audit_relative_date(answer: dict[str, Any], claim: dict[str, Any]) -> tuple[str, list[str]]:
    if not answer.get("currentDate"):
        return BLOCKED, ["relative date claim needs currentDate"]
    if claim.get("selectedDate") and DATE_RE.match(str(claim.get("selectedDate"))):
        return SUPPORTED, []
    return CONDITIONAL, ["currentDate exists, but selectedDate is not explicitly provided"]


def audit_companion_suitability(claim: dict[str, Any]) -> tuple[str, list[str]]:
    detail_patterns = [
        "/tnaDetail/response/data/description",
        "/tnaDetail/response/data/itineraries",
        "/tnaDetail/response/data/included",
        "/tnaDetail/response/data/excluded",
    ]
    if any(has_evidence(claim, pattern) for pattern in detail_patterns):
        return CONDITIONAL, ["companion suitability is indirect and needs caveated wording"]
    return BLOCKED, ["companion suitability has no cited detail evidence"]


def audit_claim(answer: dict[str, Any], evidence: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    case = find_case(evidence, claim)
    resolved, missing_paths = collect_evidence_values(case, claim)
    claim_type = claim.get("type")

    if claim_type == "availability":
        verdict, reasons = audit_availability(answer, case, claim)
    elif claim_type == "instant_confirm":
        verdict, reasons = audit_instant_confirm(case, claim)
    elif claim_type == "option_price":
        verdict, reasons = audit_option_price(case, claim)
    elif claim_type == "search_starting_price":
        verdict, reasons = audit_search_starting_price(case, claim)
    elif claim_type == "included":
        verdict, reasons = audit_list_value(case, claim, "included")
    elif claim_type == "excluded":
        verdict, reasons = audit_list_value(case, claim, "excluded")
    elif claim_type == "relative_date":
        verdict, reasons = audit_relative_date(answer, claim)
    elif claim_type == "cancellation_policy":
        verdict, reasons = BLOCKED, ["documented TNA endpoints in this MVP do not expose a cancellation-policy field"]
    elif claim_type == "reservation_or_payment_complete":
        verdict, reasons = BLOCKED, ["this MVP has no reservation or payment tool trace"]
    elif claim_type == "companion_suitability":
        verdict, reasons = audit_companion_suitability(claim)
    else:
        verdict, reasons = BLOCKED, [f"unknown claim type: {claim_type}"]

    if missing_paths:
        verdict = BLOCKED
        reasons.extend(f"unresolvable evidence path: {item}" for item in missing_paths)

    return {
        "claimId": claim.get("id"),
        "type": claim_type,
        "span": claim.get("span"),
        "caseId": case.get("caseId"),
        "verdict": verdict,
        "reasons": reasons,
        "evidencePaths": [item.get("path") for item in claim.get("evidence", []) if item.get("path")],
        "evidence": resolved,
    }


def audit(answer: dict[str, Any], evidence: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    verdicts = [audit_claim(answer, evidence, claim) for claim in answer.get("claims", [])]
    counts = Counter(item["verdict"] for item in verdicts)
    if counts[BLOCKED]:
        overall = "FAIL"
    elif counts[CONDITIONAL]:
        overall = "CONDITIONAL"
    else:
        overall = "PASS"
    return {
        "auditVersion": "0.1.0",
        "answerId": answer.get("answerId"),
        "overall": overall,
        "counts": {
            SUPPORTED: counts[SUPPORTED],
            CONDITIONAL: counts[CONDITIONAL],
            BLOCKED: counts[BLOCKED],
        },
        "policyVersion": (policy or {}).get("policyVersion"),
        "verdicts": verdicts,
    }


def korean_label(verdict: str) -> str:
    return {
        SUPPORTED: "근거 있음",
        CONDITIONAL: "확인 필요",
        BLOCKED: "근거 부족",
    }.get(verdict, verdict)


def korean_reason(reason: str) -> str:
    known_reasons = {
        "documented TNA endpoints in this MVP do not expose a cancellation-policy field": (
            "제공된 근거 데이터에는 취소 정책 근거가 없습니다"
        ),
        "this MVP has no reservation or payment tool trace": (
            "이 MVP에는 예약 또는 결제 완료를 확인하는 도구 trace가 없습니다"
        ),
        "tnaOptions selectedDate does not match claim selectedDate": (
            "옵션 조회 날짜가 답변의 날짜와 일치하지 않습니다"
        ),
        "tnaOptions options is empty or missing": (
            "해당 날짜의 예약 가능 옵션 근거가 비어 있거나 없습니다"
        ),
        "search items[].salePrice is only starting-price evidence, not final option price": (
            "검색 결과 가격은 시작가 근거일 뿐 최종 옵션 가격 근거가 아닙니다"
        ),
        "relative date claim needs currentDate": (
            "상대 날짜 표현을 확정하려면 현재 날짜가 필요합니다"
        ),
        "quantity exceeds options[].availablePurchaseQuantity": (
            "요청 인원이 구매 가능 수량을 초과합니다"
        ),
    }
    return known_reasons.get(reason, reason)


def format_korean_summary(result: dict[str, Any]) -> str:
    lines = []
    overall_label = "수정 필요" if result["overall"] == "FAIL" else (
        "확인 필요" if result["overall"] == "CONDITIONAL" else "근거 있음"
    )
    lines.append(f"전체 판단: {overall_label}")
    lines.append(
        "요약: "
        f"근거 있음 {result['counts'][SUPPORTED]}개, "
        f"확인 필요 {result['counts'][CONDITIONAL]}개, "
        f"근거 부족 {result['counts'][BLOCKED]}개"
    )
    for item in result["verdicts"]:
        lines.append(f"- {korean_label(item['verdict'])}: {item['span']}")
        if item["reasons"]:
            lines.append(f"  이유: {'; '.join(korean_reason(reason) for reason in item['reasons'])}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answer", required=True, help="Path to structured answer contract JSON")
    parser.add_argument("--evidence", required=True, help="Path to synthetic TNA evidence fixture JSON")
    parser.add_argument("--policy", required=True, help="Path to claim_policy.json")
    parser.add_argument("--output", help="Optional path for audit result JSON")
    parser.add_argument(
        "--format",
        choices=["json", "korean-summary"],
        default="json",
        help="Output format",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    result = audit(load_json(args.answer), load_json(args.evidence), load_json(args.policy))
    if args.format == "korean-summary":
        output = format_korean_summary(result)
    else:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0 if result["overall"] != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

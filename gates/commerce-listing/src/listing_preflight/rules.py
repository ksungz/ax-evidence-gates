"""Deterministic preflight rules."""

from __future__ import annotations

import re

from .input_schema import TOP_LEVEL_FIELDS
from .sources import evidence


DISCLOSURE_LABELS = {
    "material": ("01", "제품 소재"),
    "color": ("02", "색상"),
    "size": ("03", "치수"),
    "manufacturer": ("04", "제조자, 수입품의 경우 수입자"),
    "country_of_origin": ("05", "제조국"),
    "care": ("06", "세탁방법 및 취급시 주의사항"),
    "manufactured_at": ("07", "제조연월"),
    "warranty": ("08", "품질보증기준"),
    "as_contact": ("09", "A/S 책임자와 전화번호"),
}

DISCLOSURE_ORDER = [
    "material",
    "color",
    "size",
    "manufacturer",
    "country_of_origin",
    "care",
    "manufactured_at",
    "warranty",
    "as_contact",
]

SIZE_CHART_ORDER = [
    "size",
    "body_length_cm",
    "shoulder_width_cm",
    "chest_width_cm",
    "sleeve_length_cm",
]

REQUIRED_TOP_LEVEL_LABELS = {
    "product_name": "상품명",
    "category": "카테고리",
    "attributes": "속성",
    "tags": "태그",
    "disclosure": "상품 고시 정보",
    "size_chart": "사이즈표",
    "description": "상세설명",
}

MEASUREMENT_LABELS = {
    "body_length_cm": "총장",
    "shoulder_width_cm": "어깨너비",
    "chest_width_cm": "가슴 단면",
    "sleeve_length_cm": "소매 길이",
}

MEASUREMENT_RANGES = {
    "body_length_cm": (35, 110),
    "shoulder_width_cm": (25, 80),
    "chest_width_cm": (30, 90),
    "sleeve_length_cm": (20, 100),
}

SIZE_ORDER = {
    "XXS": 0,
    "XS": 1,
    "S": 2,
    "M": 3,
    "L": 4,
    "XL": 5,
    "XXL": 6,
    "2XL": 6,
    "XXXL": 7,
    "3XL": 7,
}


def run_rules(data):
    findings = []
    findings.extend(check_required_top_level(data))
    findings.extend(check_disclosure(data))
    findings.extend(check_size_chart(data))
    return findings


def check_required_top_level(data):
    findings = []
    for key in sorted(TOP_LEVEL_FIELDS):
        value = data.get(key)
        if _is_missing(value):
            findings.append(
                make_finding(
                    rule_id="REQUIRED-FIELD-MISSING",
                    severity="error",
                    title=f"{REQUIRED_TOP_LEVEL_LABELS[key]} 필수 필드 누락",
                    input_location=f"/{key}",
                    input_quote="<missing>" if key not in data else _quote(value),
                    evidence_key="public_product_disclosure",
                    suggestion_action="add",
                    suggestion_description=f"검수용 포맷의 {key} 필드를 채운 뒤 다시 실행한다.",
                    diff=_diff_missing(f"{key}", "<public-evidence-backed value>"),
                )
            )
    return findings


def check_disclosure(data):
    disclosure = data.get("disclosure")
    if not isinstance(disclosure, dict):
        return []

    findings = []
    for key in DISCLOSURE_ORDER:
        number, label = DISCLOSURE_LABELS[key]
        value = disclosure.get(key)
        if _is_missing(value):
            findings.append(
                make_finding(
                    rule_id=f"GOSI-CLOTHING-{number}-MISSING",
                    severity="error",
                    title=f"{label} 고시 항목 누락",
                    input_location=f"/disclosure/{key}",
                    input_quote="<missing>" if key not in disclosure else _quote(value),
                    evidence_key="gosi_clothing",
                    suggestion_action="add",
                    suggestion_description=f"고시 별표 (1) 의류 {number}호 '{label}'에 해당하는 값을 입력한다.",
                    diff=_diff_missing(f"disclosure.{key}", f"<{label}>"),
                )
            )

    material = disclosure.get("material")
    if isinstance(material, str) and material.strip() and not _has_percent(material):
        findings.append(
            make_finding(
                rule_id="GOSI-MATERIAL-PERCENT-MISSING",
                severity="error",
                title="제품 소재 혼용률 백분율 표기 누락",
                input_location="/disclosure/material",
                input_quote=material,
                evidence_key="gosi_material_percent",
                suggestion_action="replace",
                suggestion_description="섬유 조성 또는 혼용률을 백분율 형식으로 표기한다.",
                diff=_diff_replace("disclosure.material", material, "면 80%, 폴리에스터 20%"),
            )
        )
    return findings


def check_size_chart(data):
    chart = data.get("size_chart")
    if not isinstance(chart, list):
        return []

    findings = []
    findings.extend(_check_size_missing(chart))
    findings.extend(_check_size_unit_suspects(chart))
    findings.extend(_check_size_inversions(chart))
    return findings


def _check_size_missing(chart):
    findings = []
    for index, row in enumerate(chart):
        if not isinstance(row, dict):
            continue
        size_label = row.get("size", f"row {index}")
        for key in SIZE_CHART_ORDER:
            if key not in row or _is_missing(row.get(key)):
                label = "사이즈명" if key == "size" else MEASUREMENT_LABELS[key]
                findings.append(
                    make_finding(
                        rule_id="SIZE-MEASUREMENT-MISSING",
                        severity="error",
                        title=f"{size_label} {label} 결측",
                        input_location=f"/size_chart/{index}/{key}",
                        input_quote="<missing>" if key not in row else _quote(row.get(key)),
                        evidence_key="size_chart",
                        suggestion_action="add",
                        suggestion_description="상의 4개 실측 항목과 사이즈명을 모두 입력한다.",
                        diff=_diff_missing(f"size_chart[{index}].{key}", f"<{label}>"),
                    )
                )
    return findings


def _check_size_unit_suspects(chart):
    findings = []
    for index, row in enumerate(chart):
        if not isinstance(row, dict):
            continue
        suspects = []
        for key, label in MEASUREMENT_LABELS.items():
            value = row.get(key)
            if isinstance(value, (int, float)) and not _in_plausible_range(key, value):
                minimum, maximum = MEASUREMENT_RANGES[key]
                suspects.append(f"{label} {value:g}cm (허용 참고 범위 {minimum}-{maximum}cm)")
        if suspects:
            findings.append(
                make_finding(
                    rule_id="SIZE-UNIT-SUSPECT",
                    severity="warning",
                    title=f"{row.get('size', index)} 사이즈 단위 혼용 의심",
                    input_location=f"/size_chart/{index}",
                    input_quote="; ".join(suspects),
                    evidence_key="size_chart",
                    suggestion_action="review",
                    suggestion_description="상의 실측값을 cm 기준으로 다시 확인한다. inch 값이라면 cm로 환산해 입력한다.",
                    diff=_diff_replace(
                        f"size_chart[{index}]",
                        "; ".join(suspects),
                        "cm 기준 실측값",
                    ),
                )
            )
    return findings


def _check_size_inversions(chart):
    findings = []
    ordered_rows = [
        (SIZE_ORDER.get(str(row.get("size", "")).upper()), index, row)
        for index, row in enumerate(chart)
        if isinstance(row, dict) and str(row.get("size", "")).upper() in SIZE_ORDER
    ]
    ordered_rows.sort(key=lambda item: item[0])

    for (_, prev_index, prev), (_, curr_index, curr) in zip(ordered_rows, ordered_rows[1:]):
        for key, label in MEASUREMENT_LABELS.items():
            prev_value = prev.get(key)
            curr_value = curr.get(key)
            if not (
                isinstance(prev_value, (int, float))
                and isinstance(curr_value, (int, float))
                and _in_plausible_range(key, prev_value)
                and _in_plausible_range(key, curr_value)
            ):
                continue
            if curr_value + 0.01 < prev_value:
                quote = (
                    f"{prev.get('size')} {label} {prev_value:g}cm > "
                    f"{curr.get('size')} {label} {curr_value:g}cm"
                )
                findings.append(
                    make_finding(
                        rule_id="SIZE-ORDER-INVERSION",
                        severity="warning",
                        title=f"{label} 사이즈 간 역전값",
                        input_location=f"/size_chart/{prev_index}/{key}..{curr_index}/{key}",
                        input_quote=quote,
                        evidence_key="size_chart",
                        suggestion_action="review",
                        suggestion_description="사이즈표 원본을 확인해 큰 사이즈의 실측값이 작아진 이유를 검토한다.",
                        diff=_diff_replace(
                            f"size_chart[{curr_index}].{key}",
                            f"{curr_value:g}",
                            f">= {prev_value:g}",
                        ),
                    )
                )
    return findings


def make_finding(
    rule_id,
    severity,
    title,
    input_location,
    input_quote,
    evidence_key,
    suggestion_action,
    suggestion_description,
    diff,
):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "input_location": input_location,
        "input_quote": str(input_quote),
        "evidence": evidence(evidence_key),
        "suggestion": {
            "action": suggestion_action,
            "description": suggestion_description,
            "diff": diff,
        },
    }


def _is_missing(value):
    return value is None or value == "" or value == [] or value == {}


def _quote(value):
    if isinstance(value, str):
        return value
    return repr(value)


def _has_percent(value):
    return bool(re.search(r"\d+(?:\.\d+)?\s*%", value))


def _in_plausible_range(key, value):
    minimum, maximum = MEASUREMENT_RANGES[key]
    return minimum <= value <= maximum


def _diff_missing(path, value):
    return f"--- original\n+++ suggested\n@@\n- {path}: <missing>\n+ {path}: {value}"


def _diff_replace(path, old, new):
    return f"--- original\n+++ suggested\n@@\n- {path}: {old}\n+ {path}: {new}"

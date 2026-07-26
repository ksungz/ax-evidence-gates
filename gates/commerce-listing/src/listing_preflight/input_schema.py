"""Input loading and narrow validation for listing-preflight examples."""

from __future__ import annotations

import json
from pathlib import Path


class InputError(Exception):
    """Raised when the input JSON cannot be processed safely."""


TOP_LEVEL_FIELDS = {
    "product_name",
    "category",
    "attributes",
    "tags",
    "disclosure",
    "size_chart",
    "description",
}

CATEGORY_FIELDS = {"main", "sub"}
ATTRIBUTE_GROUPS = {"components", "design", "material_traits", "sensibility"}
DISCLOSURE_FIELDS = {
    "material",
    "color",
    "size",
    "manufacturer",
    "country_of_origin",
    "care",
    "manufactured_at",
    "warranty",
    "as_contact",
}
SIZE_CHART_FIELDS = {
    "size",
    "body_length_cm",
    "shoulder_width_cm",
    "chest_width_cm",
    "sleeve_length_cm",
}


def load_listing(path):
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read input file: {path}: {exc}") from exc

    if not raw.strip():
        raise InputError(f"empty input file: {path}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc

    validate_listing_shape(data)
    return data


def validate_listing_shape(data):
    if not isinstance(data, dict):
        raise InputError("input root must be a JSON object")

    _reject_unknown(data, TOP_LEVEL_FIELDS, "")

    if "product_name" in data and not isinstance(data["product_name"], str):
        raise InputError("product_name must be a string")
    if "description" in data and not isinstance(data["description"], str):
        raise InputError("description must be a string")

    if "category" in data:
        _require_object(data["category"], "category")
        _reject_unknown(data["category"], CATEGORY_FIELDS, "/category")
        for key in CATEGORY_FIELDS:
            if key in data["category"] and not isinstance(data["category"][key], str):
                raise InputError(f"category.{key} must be a string")

    if "attributes" in data:
        _require_object(data["attributes"], "attributes")
        _reject_unknown(data["attributes"], ATTRIBUTE_GROUPS, "/attributes")
        for group, value in data["attributes"].items():
            _require_object(value, f"attributes.{group}")
            for attr_key, attr_value in value.items():
                if not isinstance(attr_key, str) or not isinstance(attr_value, str):
                    raise InputError(f"attributes.{group} values must be strings")

    if "tags" in data:
        if not isinstance(data["tags"], list):
            raise InputError("tags must be an array")
        if any(not isinstance(tag, str) for tag in data["tags"]):
            raise InputError("tags values must be strings")

    if "disclosure" in data:
        _require_object(data["disclosure"], "disclosure")
        _reject_unknown(data["disclosure"], DISCLOSURE_FIELDS, "/disclosure")
        for key, value in data["disclosure"].items():
            if not isinstance(value, str):
                raise InputError(f"disclosure.{key} must be a string")

    if "size_chart" in data:
        if not isinstance(data["size_chart"], list):
            raise InputError("size_chart must be an array")
        for index, row in enumerate(data["size_chart"]):
            _require_object(row, f"size_chart[{index}]")
            _reject_unknown(row, SIZE_CHART_FIELDS, f"/size_chart/{index}")
            if "size" in row and not isinstance(row["size"], str):
                raise InputError(f"size_chart[{index}].size must be a string")
            for key in SIZE_CHART_FIELDS - {"size"}:
                if key in row and not isinstance(row[key], (int, float)):
                    raise InputError(f"size_chart[{index}].{key} must be a number")


def _reject_unknown(obj, allowed, pointer):
    unknown = sorted(set(obj) - allowed)
    if unknown:
        location = pointer or "root"
        raise InputError(f"unknown field at {location}: {unknown[0]}")


def _require_object(value, name):
    if not isinstance(value, dict):
        raise InputError(f"{name} must be an object")

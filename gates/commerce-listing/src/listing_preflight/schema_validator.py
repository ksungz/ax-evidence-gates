"""Small JSON Schema validator for the strict report schema used here.

It intentionally supports only the schema keywords this repository uses. That
keeps the demo dependency-free while still validating against a JSON Schema
document stored in src/schemas/report.schema.json.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


class SchemaValidationError(Exception):
    """Raised when validation fails."""


def validate(instance, schema, path="$"):
    errors = list(iter_errors(instance, schema, path))
    if errors:
        raise SchemaValidationError("\n".join(errors))


def iter_errors(instance, schema, path="$"):
    expected_type = schema.get("type")
    if expected_type and not _matches_type(instance, expected_type):
        yield f"{path}: expected {expected_type}, got {type(instance).__name__}"
        return

    if "const" in schema and instance != schema["const"]:
        yield f"{path}: expected const {schema['const']!r}"

    if "enum" in schema and instance not in schema["enum"]:
        yield f"{path}: expected one of {schema['enum']!r}"

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                yield f"{path}: missing required property {key!r}"

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in sorted(set(instance) - set(properties)):
                yield f"{path}: additional property {key!r} is not allowed"

        for key, subschema in properties.items():
            if key in instance:
                yield from iter_errors(instance[key], subschema, f"{path}.{key}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            yield f"{path}: expected at least {schema['minItems']} items"
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            yield f"{path}: expected at most {schema['maxItems']} items"
        item_schema = schema.get("items")
        if item_schema:
            for index, value in enumerate(instance):
                yield from iter_errors(value, item_schema, f"{path}[{index}]")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            yield f"{path}: expected minLength {schema['minLength']}"
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            yield f"{path}: does not match pattern {schema['pattern']!r}"
        if schema.get("format") == "uri" and not _is_uri(instance):
            yield f"{path}: expected uri"

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            yield f"{path}: expected minimum {schema['minimum']}"


def _matches_type(instance, expected):
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    raise ValueError(f"unsupported schema type: {expected}")


def _is_uri(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

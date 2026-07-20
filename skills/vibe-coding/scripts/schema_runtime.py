#!/usr/bin/env python3
"""Small JSON Schema 2020-12 subset used by Vibe Coding contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"only local schema references are supported: {reference}")
    target: Any = root
    for component in reference[2:].split("/"):
        target = target[component.replace("~1", "/").replace("~0", "~")]
    if not isinstance(target, dict):
        raise ValueError(f"schema reference does not resolve to an object: {reference}")
    return target


def _type_matches(value: Any, expected: str) -> bool:
    return {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }[expected](value)


def _validate(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    if "$ref" in schema:
        return _validate(value, _resolve_ref(root, schema["$ref"]), root, path)
    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} must be one of {schema['enum']!r}")
    expected_types = schema.get("type")
    if isinstance(expected_types, str):
        expected_types = [expected_types]
    if isinstance(expected_types, list) and not any(_type_matches(value, item) for item in expected_types):
        return errors + [f"{path} has the wrong type; expected {expected_types!r}"]

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key} is required")
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key in properties:
                errors.extend(_validate(item, properties[key], root, item_path))
            elif additional is False:
                errors.append(f"{item_path} is not allowed by the published schema")
            elif isinstance(additional, dict):
                errors.extend(_validate(item, additional, root, item_path))
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path} has too few properties")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path} has too few items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path} must contain unique items")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                errors.extend(_validate(item, schema["items"], root, f"{path}[{index}]"))
        if isinstance(schema.get("contains"), dict) and not any(
            not _validate(item, schema["contains"], root, f"{path}[*]") for item in value
        ):
            errors.append(f"{path} does not contain a required item")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path} is shorter than the published minimum")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path} does not match the published pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} is below the published minimum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path} must be greater than the published minimum")

    for subschema in schema.get("allOf", []):
        errors.extend(_validate(value, subschema, root, path))
    condition = schema.get("if")
    if isinstance(condition, dict) and not _validate(value, condition, root, path):
        if isinstance(schema.get("then"), dict):
            errors.extend(_validate(value, schema["then"], root, path))
    return errors


def validate_instance(value: Any, schema_path: Path, label: str) -> list[str]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        return [f"{label} schema: {error}" for error in _validate(value, schema, schema, "$")]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
        return [f"{label} schema cannot be applied: {exc}"]

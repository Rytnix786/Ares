from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ares.api.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
GOLDEN_SCHEMA_PATH = Path("tests/golden/openapi_schema.json")


def _iter_operations(schema: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, operations in schema.get("paths", {}).items():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                yield path, method.lower(), operation


def _resolve_schema(node: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return {}
        resolved: Any = schema
        for part in ref[2:].split("/"):
            if not isinstance(resolved, dict):
                return {}
            resolved = resolved.get(part)
            if resolved is None:
                return {}
        return _resolve_schema(resolved, schema) if isinstance(resolved, dict) else {}
    if "allOf" in node:
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for item in node.get("allOf", []):
            resolved = _resolve_schema(item, schema)
            merged["required"].extend(resolved.get("required", []))
            merged["properties"].update(resolved.get("properties", {}))
        merged["required"] = sorted(set(merged["required"]))
        return merged
    return node


def _collect_required_request_fields(
    node: dict[str, Any],
    schema: dict[str, Any],
    *,
    prefix: str = "",
) -> set[str]:
    resolved = _resolve_schema(node, schema)
    fields: set[str] = set()
    required = resolved.get("required", [])
    properties = resolved.get("properties", {})
    if not isinstance(required, list) or not isinstance(properties, dict):
        return fields
    for name in required:
        property_schema = properties.get(name, {})
        if not isinstance(name, str) or not isinstance(property_schema, dict):
            continue
        path = f"{prefix}.{name}" if prefix else name
        fields.add(path)
        fields |= _collect_required_request_fields(property_schema, schema, prefix=path)
    return fields


def _collect_response_fields(
    node: dict[str, Any],
    schema: dict[str, Any],
    *,
    prefix: str = "",
) -> set[str]:
    resolved = _resolve_schema(node, schema)
    fields: set[str] = set()
    if "allOf" in resolved:
        for item in resolved.get("allOf", []):
            fields |= _collect_response_fields(item, schema, prefix=prefix)
        return fields
    schema_type = resolved.get("type")
    if schema_type == "array" and isinstance(resolved.get("items"), dict):
        item_prefix = f"{prefix}[]" if prefix else "[]"
        fields |= _collect_response_fields(resolved["items"], schema, prefix=item_prefix)
        return fields
    properties = resolved.get("properties", {})
    if not isinstance(properties, dict):
        return fields
    for name, property_schema in properties.items():
        if not isinstance(name, str) or not isinstance(property_schema, dict):
            continue
        path = f"{prefix}.{name}" if prefix else name
        fields.add(path)
        fields |= _collect_response_fields(property_schema, schema, prefix=path)
    return fields


def _request_schema_fields(operation: dict[str, Any], schema: dict[str, Any]) -> set[str]:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return set()
    content = request_body.get("content", {})
    if not isinstance(content, dict):
        return set()
    fields: set[str] = set()
    for media_type in content.values():
        if not isinstance(media_type, dict):
            continue
        media_schema = media_type.get("schema")
        if isinstance(media_schema, dict):
            fields |= _collect_required_request_fields(media_schema, schema)
    return fields


def _response_schema_fields(operation: dict[str, Any], schema: dict[str, Any]) -> dict[str, set[str]]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return {}
    response_fields: dict[str, set[str]] = {}
    for status_code, response in responses.items():
        if not isinstance(status_code, str) or not isinstance(response, dict):
            continue
        content = response.get("content", {})
        if not isinstance(content, dict):
            response_fields[status_code] = set()
            continue
        fields: set[str] = set()
        for media_type in content.values():
            if not isinstance(media_type, dict):
                continue
            media_schema = media_type.get("schema")
            if isinstance(media_schema, dict):
                fields |= _collect_response_fields(media_schema, schema)
        response_fields[status_code] = fields
    return response_fields


def _load_live_schema() -> dict[str, Any]:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return dict(response.json())


def _load_or_generate_golden(live_schema: dict[str, Any]) -> dict[str, Any]:
    if GOLDEN_SCHEMA_PATH.exists():
        return json.loads(GOLDEN_SCHEMA_PATH.read_text(encoding="utf-8"))
    GOLDEN_SCHEMA_PATH.write_text(
        json.dumps(live_schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("Golden schema generated — commit this file")
    pytest.fail("Golden schema generated — commit this file")


def test_openapi_schema_remains_backward_compatible() -> None:
    live_schema = _load_live_schema()
    golden_schema = _load_or_generate_golden(live_schema)

    golden_operations = {
        (path, method): operation for path, method, operation in _iter_operations(golden_schema)
    }
    live_operations = {
        (path, method): operation for path, method, operation in _iter_operations(live_schema)
    }

    removed_operations = sorted(set(golden_operations) - set(live_operations))
    assert not removed_operations, f"Removed OpenAPI operations: {removed_operations}"

    removed_request_fields: list[str] = []
    removed_response_fields: list[str] = []

    for operation_key, golden_operation in golden_operations.items():
        live_operation = live_operations[operation_key]
        golden_required = _request_schema_fields(golden_operation, golden_schema)
        live_required = _request_schema_fields(live_operation, live_schema)
        missing_required = sorted(golden_required - live_required)
        if missing_required:
            method = operation_key[1].upper()
            path = operation_key[0]
            removed_request_fields.extend(
                [f"{method} {path}: {field}" for field in missing_required]
            )

        golden_responses = _response_schema_fields(golden_operation, golden_schema)
        live_responses = _response_schema_fields(live_operation, live_schema)
        missing_statuses = sorted(set(golden_responses) - set(live_responses))
        if missing_statuses:
            method = operation_key[1].upper()
            path = operation_key[0]
            removed_response_fields.extend(
                [f"{method} {path}: missing response {status_code}" for status_code in missing_statuses]
            )
            continue
        for status_code, golden_fields in golden_responses.items():
            missing_fields = sorted(golden_fields - live_responses.get(status_code, set()))
            if missing_fields:
                method = operation_key[1].upper()
                path = operation_key[0]
                removed_response_fields.extend(
                    [f"{method} {path} {status_code}: {field}" for field in missing_fields]
                )

    assert not removed_request_fields, (
        "Removed required request-body fields:\n" + "\n".join(removed_request_fields)
    )
    assert not removed_response_fields, (
        "Removed response fields:\n" + "\n".join(removed_response_fields)
    )

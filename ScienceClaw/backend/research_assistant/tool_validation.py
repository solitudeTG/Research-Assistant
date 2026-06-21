from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tool_decorator_name(decorator: ast.expr) -> str:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call):
        return _tool_decorator_name(decorator.func)
    return ""


def _find_tool_function(module: ast.Module, tool_name: str) -> ast.FunctionDef | None:
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != tool_name:
            continue
        if any(_tool_decorator_name(decorator) == "tool" for decorator in node.decorator_list):
            return node
    return None


def _schema_for_value(value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        item_schema: Dict[str, Any] = {}
        if value:
            item_schema = _schema_for_value(value[0])
        return {"type": "array", "items": item_schema}
    if isinstance(value, dict):
        properties = {str(key): _schema_for_value(item) for key, item in value.items()}
        return {
            "type": "object",
            "properties": properties,
            "required": [str(key) for key in value.keys()],
        }
    if value is None:
        return {"type": "null"}
    return {"type": "string"}


def _write_sidecar(staging_dir: Path, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    sidecar = staging_dir / f"{tool_name}.validation.json"
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def validate_staged_tool(
    staging_dir: str | Path,
    tool_name: str,
    *,
    example_args: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    staging_path = Path(staging_dir)
    tool_path = staging_path / f"{tool_name}.py"
    checks = []

    base_payload: Dict[str, Any] = {
        "tool_name": tool_name,
        "validated_at": _utc_now_iso(),
    }

    if not tool_path.is_file():
        return _write_sidecar(
            staging_path,
            tool_name,
            {
                **base_payload,
                "status": "failed",
                "checks": checks,
                "error": f"Tool file not found: {tool_name}.py",
            },
        )

    source = tool_path.read_text(encoding="utf-8", errors="replace")
    try:
        module = ast.parse(source, filename=str(tool_path))
    except SyntaxError as exc:
        return _write_sidecar(
            staging_path,
            tool_name,
            {
                **base_payload,
                "status": "failed",
                "checks": checks,
                "error": f"Python syntax error: {exc.msg}",
            },
        )
    checks.append("python_syntax")

    tool_function = _find_tool_function(module, tool_name)
    if tool_function is None:
        return _write_sidecar(
            staging_path,
            tool_name,
            {
                **base_payload,
                "status": "failed",
                "checks": checks,
                "error": f"No @tool-decorated function named {tool_name}",
            },
        )
    checks.append("tool_function")

    safe_builtins = {
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "round": round,
        "str": str,
        "sum": sum,
    }
    namespace: Dict[str, Any] = {
        "__builtins__": safe_builtins,
        "tool": lambda fn=None, **_kwargs: fn if fn is not None else (lambda wrapped: wrapped),
    }
    try:
        exec(compile(module, str(tool_path), "exec"), namespace)
        result = namespace[tool_name](**(example_args or {}))
    except Exception as exc:
        return _write_sidecar(
            staging_path,
            tool_name,
            {
                **base_payload,
                "status": "failed",
                "checks": checks,
                "error": f"Example call failed: {exc}",
            },
        )
    checks.append("example_call")

    return_schema = _schema_for_value(result)
    checks.append("return_schema")

    return _write_sidecar(
        staging_path,
        tool_name,
        {
            **base_payload,
            "status": "passed",
            "checks": checks,
            "return_schema": return_schema,
            "example_output": result,
        },
    )

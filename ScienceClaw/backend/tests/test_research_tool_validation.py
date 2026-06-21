import json
import hashlib

from backend.research_assistant.tool_validation import validate_staged_tool


def test_validate_staged_tool_writes_passed_sidecar_with_return_schema(tmp_path):
    staging = tmp_path / "tools_staging"
    staging.mkdir()
    source = (
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query, "doi": "10.1234/example"}\n'
    )
    (staging / "paper_lookup.py").write_text(
        source,
        encoding="utf-8",
    )

    payload = validate_staged_tool(
        staging,
        "paper_lookup",
        example_args={"query": "evidence boundaries"},
    )

    assert payload["tool_name"] == "paper_lookup"
    assert payload["status"] == "passed"
    assert payload["checks"] == [
        "python_syntax",
        "tool_function",
        "example_call",
        "input_schema",
        "return_schema",
    ]
    assert payload["input_schema"] == {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
        },
        "required": ["query"],
    }
    assert payload["return_schema"] == {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "doi": {"type": "string"},
        },
        "required": ["title", "doi"],
    }
    assert payload["example_output"] == {
        "title": "evidence boundaries",
        "doi": "10.1234/example",
    }
    assert payload["execution_environment"] == {
        "type": "local_restricted",
        "imports_allowed": False,
    }
    assert payload["source_sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()

    sidecar = json.loads((staging / "paper_lookup.validation.json").read_text(encoding="utf-8"))
    assert sidecar == payload


def test_validate_staged_tool_writes_failed_sidecar_for_invalid_tool(tmp_path):
    staging = tmp_path / "tools_staging"
    staging.mkdir()
    (staging / "paper_lookup.py").write_text(
        'def paper_lookup(query: str) -> dict:\n'
        '    return {"title": query}\n',
        encoding="utf-8",
    )

    payload = validate_staged_tool(
        staging,
        "paper_lookup",
        example_args={"query": "evidence boundaries"},
    )

    assert payload["tool_name"] == "paper_lookup"
    assert payload["status"] == "failed"
    assert payload["checks"] == ["python_syntax"]
    assert "No @tool-decorated function" in payload["error"]
    assert "return_schema" not in payload

    sidecar = json.loads((staging / "paper_lookup.validation.json").read_text(encoding="utf-8"))
    assert sidecar == payload


def test_validate_staged_tool_rejects_imports_in_validation_runner(tmp_path):
    staging = tmp_path / "tools_staging"
    staging.mkdir()
    (staging / "paper_lookup.py").write_text(
        'import os\n'
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"cwd": os.getcwd(), "title": query}\n',
        encoding="utf-8",
    )

    payload = validate_staged_tool(
        staging,
        "paper_lookup",
        example_args={"query": "evidence boundaries"},
    )

    assert payload["tool_name"] == "paper_lookup"
    assert payload["status"] == "failed"
    assert payload["checks"] == ["python_syntax", "tool_function"]
    assert "Example call failed" in payload["error"]
    assert "return_schema" not in payload

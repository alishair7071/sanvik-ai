"""Check the public run_task IPC operation without launching desktop apps."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from sanvik_agent.agent import workflow
from sanvik_agent.ipc.runtime import handle_line, serve


def request(message: str, operation: str = "run_task") -> str:
    return json.dumps({
        "version": 1,
        "type": "request",
        "id": "task-1",
        "payload": {"operation": operation, "message": message},
    })


def test_run_response_contains_plan_and_execution(monkeypatch) -> None:
    expected = {
        "plan": {"goal": "Open Notepad", "steps": []},
        "execution": {"completed": True, "steps": []},
    }
    monkeypatch.setattr(workflow, "run_task", lambda task: expected)

    response, stop = handle_line(request("Open Notepad"))
    assert not stop
    assert response["id"] == "task-1"
    assert response["success"] is True
    assert response["payload"] == expected


def test_missing_key_is_controlled(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    response, stop = handle_line(request("Open Notepad"))
    assert not stop
    assert response["error"]["code"] == "missing_api_key"


def test_empty_task_and_unexpected_error_are_controlled(monkeypatch) -> None:
    response, _ = handle_line(request("  "))
    assert response["error"]["code"] == "empty_task"

    def broken(task: str) -> dict:
        raise RuntimeError("internal detail")

    monkeypatch.setattr(workflow, "run_task", broken)
    response, _ = handle_line(request("Open Notepad"))
    assert response["error"]["code"] == "internal_error"
    assert "internal detail" not in response["error"]["message"]


def test_subprocess_returns_controlled_missing_key(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    package_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_root / "src")
    result = subprocess.run(
        [sys.executable, "-u", "-m", "sanvik_agent.ipc.runtime"],
        input=request("Open Notepad") + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=package_root,
        env=env,
        timeout=10,
        check=True,
    )
    response = json.loads(result.stdout)
    assert response["id"] == "task-1"
    assert response["error"]["code"] == "missing_api_key"


def test_serve_round_trip_with_fake_runner(monkeypatch) -> None:
    expected = {
        "plan": {"goal": "Open Notepad", "steps": []},
        "execution": {"completed": True, "steps": []},
    }
    monkeypatch.setattr(workflow, "run_task", lambda task: expected)
    output = io.StringIO()
    serve(io.StringIO(request("Open Notepad") + "\n"), output)

    reply = json.loads(output.getvalue())
    assert reply["id"] == "task-1"
    assert reply["success"] is True
    assert reply["payload"] == expected


def test_plan_only_operation_is_removed() -> None:
    response, stop = handle_line(request("Open Notepad", "plan_task"))
    assert not stop
    assert response["error"]["code"] == "unknown_operation"

import json
import os
import subprocess
import sys
from pathlib import Path

from sanvik_agent.agent.planning.plan import Plan
from sanvik_agent.ipc.runtime import handle_line


def request(message: str) -> str:
    return json.dumps({
        "version": 1,
        "type": "request",
        "id": "planning-1",
        "payload": {"operation": "plan_task", "message": message},
    })


def test_planning_response_contains_structured_plan() -> None:
    expected = Plan.model_validate({
        "goal": "Open Notepad",
        "steps": [{
            "action": "launch_app",
            "parameters": {"app": "Notepad"},
            "expected_result": "Notepad is open",
            "risk_level": "READ_ONLY",
        }],
    })
    response, stop = handle_line(request("Open Notepad"), planner=lambda task: expected)
    assert not stop
    assert response["id"] == "planning-1"
    assert response["success"] is True
    assert response["payload"]["plan"] == expected.model_dump(mode="json")


def test_missing_key_is_controlled(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    response, stop = handle_line(request("Open Notepad"))
    assert not stop
    assert response["error"]["code"] == "missing_api_key"


def test_empty_task_and_unexpected_error_are_controlled() -> None:
    response, _ = handle_line(request("  "))
    assert response["error"]["code"] == "empty_task"

    def broken(task: str) -> Plan:
        raise RuntimeError("internal detail")

    response, _ = handle_line(request("Open Notepad"), planner=broken)
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
    assert response["id"] == "planning-1"
    assert response["error"]["code"] == "missing_api_key"
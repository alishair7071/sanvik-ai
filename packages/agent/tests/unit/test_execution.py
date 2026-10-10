import pytest

from sanvik_agent.agent.plan import Plan
from sanvik_agent.execution import executor


def notepad_plan(text="Hello") -> Plan:
    return Plan.model_validate({
        "goal": "Open Notepad and type Hello",
        "steps": [
            {"action": "launch_app", "parameters": {"app": "notepad"},
             "expected_result": "Notepad is open", "risk_level": "READ_ONLY"},
            {"action": "type_text", "parameters": {"text": text},
             "expected_result": "Text appears", "risk_level": "REVERSIBLE"},
            {"action": "verify_result", "parameters": {},
             "expected_result": "Text is visible", "risk_level": "READ_ONLY"},
        ],
    })


def test_notepad_plan_runs_and_verifies_each_step(monkeypatch) -> None:
    window = object()
    calls = []
    monkeypatch.setattr(executor, "open_notepad", lambda: window)
    monkeypatch.setattr(executor, "write_text", lambda target, text: calls.append(("write", target, text)))
    monkeypatch.setattr(executor, "verify_notepad", lambda target, text: calls.append(("verify", target, text)))

    result = executor.execute_plan(notepad_plan())

    assert result["completed"] is True
    assert [step["success"] for step in result["steps"]] == [True, True, True]
    assert calls == [("verify", window, None), ("write", window, "Hello"), ("verify", window, "Hello")]


@pytest.mark.parametrize("action,parameters,risk", [
    ("launch_app", {"app": "powershell"}, "READ_ONLY"),
    ("run_command", {"command": "echo hi"}, "READ_ONLY"),
    ("type_text", {"text": "Hello"}, "SENSITIVE"),
])
def test_unsupported_plan_stops_before_any_action(monkeypatch, action, parameters, risk) -> None:
    opened = []
    monkeypatch.setattr(executor, "open_notepad", lambda: opened.append(True))
    plan = notepad_plan()
    plan.steps[1].action = action
    plan.steps[1].parameters = parameters
    plan.steps[1].risk_level = risk

    with pytest.raises(executor.UnsupportedPlan):
        executor.execute_plan(plan)
    assert opened == []


def test_failed_text_step_stops_execution(monkeypatch) -> None:
    window = object()
    monkeypatch.setattr(executor, "open_notepad", lambda: window)
    monkeypatch.setattr(executor, "verify_notepad", lambda target, text: None)

    def fail_to_write(target, text):
        raise RuntimeError("editor unavailable")

    monkeypatch.setattr(executor, "write_text", fail_to_write)
    result = executor.execute_plan(notepad_plan())
    assert result["completed"] is False
    assert [step["success"] for step in result["steps"]] == [True, False]
    assert "editor unavailable" not in result["steps"][-1]["message"]

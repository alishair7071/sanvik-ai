import pytest

from sanvik_agent.agent.plan import Plan
from sanvik_agent.execution import executor


def make_plan(steps) -> Plan:
    return Plan.model_validate({"goal": "Application task", "steps": steps})


def step(action, parameters, risk="REVERSIBLE") -> dict:
    return {
        "action": action,
        "parameters": parameters,
        "expected_result": "Visible result",
        "risk_level": risk,
    }


def typing_plan() -> Plan:
    return make_plan([
        step("open_application", {"application": "notepad"}),
        step("type_text", {"text": "Hello"}),
        step("verify_text", {"text": "Hello"}, "READ_ONLY"),
    ])


def open_only_plan(application: str) -> Plan:
    return make_plan([
        step("open_application", {"application": application}),
        step("verify_application", {}, "READ_ONLY"),
    ])


def test_notepad_opens_types_and_verifies(monkeypatch) -> None:
    window = object()
    calls = []
    monkeypatch.setattr(
        executor,
        "open_application",
        lambda executable: calls.append(("open", executable)) or window,
    )
    monkeypatch.setattr(
        executor,
        "type_text",
        lambda target, text: calls.append(("type", target, text)),
    )
    monkeypatch.setattr(
        executor,
        "verify_text",
        lambda target, text: calls.append(("verify_text", target, text)),
    )

    result = executor.execute_plan(typing_plan())

    assert result["completed"] is True
    assert calls == [
        ("open", "notepad.exe"),
        ("type", window, "Hello"),
        ("verify_text", window, "Hello"),
    ]
    assert [item["message"] for item in result["steps"]] == [
        "Completed", "Completed", "Verified"
    ]


@pytest.mark.parametrize(
    "application,expected_executable",
    [
        ("notepad", "notepad.exe"),
        ("file_explorer", "explorer.exe"),
        ("chrome", "chrome.exe"),
    ],
)
def test_supported_application_can_open(
    monkeypatch, application, expected_executable
) -> None:
    window = object()
    calls = []
    monkeypatch.setattr(
        executor,
        "open_application",
        lambda executable: calls.append(("open", executable)) or window,
    )
    monkeypatch.setattr(
        executor,
        "verify_application",
        lambda target: calls.append(("verify", target)),
    )

    result = executor.execute_plan(open_only_plan(application))

    assert result["completed"] is True
    assert calls == [("open", expected_executable), ("verify", window)]


@pytest.mark.parametrize("application", [
    "mspaint",
    "code",
    "cmd",
    "unknown_application",
])
def test_unsupported_application_is_rejected_before_launch(
    monkeypatch, application
) -> None:
    opened = []
    monkeypatch.setattr(
        executor,
        "open_application",
        lambda executable: opened.append(executable),
    )

    with pytest.raises(executor.UnsupportedPlan):
        executor.execute_plan(open_only_plan(application))
    assert opened == []


@pytest.mark.parametrize("steps", [
    [step("open_recycle_bin", {}), step("verify_application", {}, "READ_ONLY")],
    [step("launch_app", {"app": "Notepad"}), step("verify_application", {})],
    [
        step("open_application", {"executable": "notepad.exe"}),
        step("verify_application", {}, "READ_ONLY"),
    ],
    [step("open_application", {"application": "notepad"})],
    [
        step("open_application", {"application": "notepad"}),
        step("type_text", {"text": "Hello"}, "SENSITIVE"),
        step("verify_text", {"text": "Hello"}, "READ_ONLY"),
    ],
    [
        step("open_application", {"application": "notepad"}),
        step("type_text", {"text": "Hello"}),
        step("verify_text", {"text": "different"}, "READ_ONLY"),
    ],
])
def test_invalid_plan_is_rejected_before_launch(monkeypatch, steps) -> None:
    opened = []
    monkeypatch.setattr(
        executor,
        "open_application",
        lambda executable: opened.append(executable),
    )

    with pytest.raises(executor.UnsupportedPlan):
        executor.execute_plan(make_plan(steps))
    assert opened == []


@pytest.mark.parametrize("application", ["file_explorer", "chrome"])
def test_typing_is_rejected_for_applications_other_than_notepad(
    monkeypatch, application
) -> None:
    opened = []
    monkeypatch.setattr(
        executor,
        "open_application",
        lambda executable: opened.append(executable),
    )
    plan = make_plan([
        step("open_application", {"application": application}),
        step("type_text", {"text": "Hello"}),
        step("verify_text", {"text": "Hello"}, "READ_ONLY"),
    ])

    with pytest.raises(executor.UnsupportedPlan):
        executor.execute_plan(plan)
    assert opened == []


def test_failed_text_step_stops_execution(monkeypatch) -> None:
    window = object()
    monkeypatch.setattr(executor, "open_application", lambda executable: window)

    def fail_to_type(target, text):
        raise RuntimeError("editor unavailable")

    monkeypatch.setattr(executor, "type_text", fail_to_type)
    result = executor.execute_plan(typing_plan())

    assert result["completed"] is False
    assert [item["success"] for item in result["steps"]] == [True, False]
    assert "editor unavailable" not in result["steps"][-1]["message"]

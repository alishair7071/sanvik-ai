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


def close_only_plan(application: str, close_all: bool = False) -> Plan:
    parameters = {"application": application}

    if close_all:
        parameters["scope"] = "all"

    return make_plan([
        step("close_application", parameters, "SENSITIVE"),
        step("verify_application_closed", {}, "READ_ONLY"),
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

@pytest.mark.parametrize("application", ["chrome", "file_explorer"])
def test_supported_application_can_close(monkeypatch, application) -> None:
    window = object()
    calls = []

    monkeypatch.setattr(
        executor,
        "find_application_windows",
        lambda name: calls.append(("find", name)) or [window],
    )
    monkeypatch.setattr(
        executor,
        "close_application",
        lambda target: calls.append(("close", target)),
    )
    monkeypatch.setattr(
        executor,
        "verify_application_closed",
        lambda target: calls.append(("verify_closed", target)),
    )

    result = executor.execute_plan(close_only_plan(application))

    assert result["completed"] is True
    assert calls == [
        ("find", application),
        ("close", window),
        ("verify_closed", window),
    ]


def test_already_closed_application_is_successful(monkeypatch) -> None:
    monkeypatch.setattr(executor, "find_application_windows", lambda name: [])

    result = executor.execute_plan(close_only_plan("chrome"))

    assert result["completed"] is True
    assert result["steps"][0]["message"] == "Application was already closed"
    assert result["steps"][1]["message"] == "Verified"


def test_multiple_windows_are_not_closed_automatically(monkeypatch) -> None:
    closed = []
    monkeypatch.setattr(
        executor,
        "find_application_windows",
        lambda name: [object(), object()],
    )
    monkeypatch.setattr(
        executor,
        "close_application",
        lambda window: closed.append(window),
    )

    result = executor.execute_plan(close_only_plan("chrome"))

    assert result["completed"] is False
    assert "2 application windows" in result["steps"][0]["message"]
    assert closed == []


def test_explicit_close_all_closes_and_verifies_every_window(monkeypatch) -> None:
    first_window = object()
    second_window = object()
    closed = []
    verified = []

    monkeypatch.setattr(
        executor,
        "find_application_windows",
        lambda name: [first_window, second_window],
    )
    monkeypatch.setattr(
        executor,
        "close_application",
        lambda window: closed.append(window),
    )
    monkeypatch.setattr(
        executor,
        "verify_application_closed",
        lambda window: verified.append(window),
    )

    result = executor.execute_plan(close_only_plan("chrome", close_all=True))

    assert result["completed"] is True
    assert result["steps"][0]["message"] == "Closed 2 application windows"
    assert closed == [first_window, second_window]
    assert verified == [first_window, second_window]


def test_notepad_closing_is_not_supported(monkeypatch) -> None:
    found = []
    monkeypatch.setattr(
        executor,
        "find_application_windows",
        lambda name: found.append(name),
    )

    with pytest.raises(executor.UnsupportedPlan, match="Closing is supported only"):
        executor.execute_plan(close_only_plan("notepad"))

    assert found == []


def test_close_plan_requires_sensitive_risk() -> None:
    plan = make_plan([
        step("close_application", {"application": "chrome"}, "REVERSIBLE"),
        step("verify_application_closed", {}, "READ_ONLY"),
    ])

    with pytest.raises(executor.UnsupportedPlan, match="SENSITIVE"):
        executor.execute_plan(plan)

def test_invalid_close_scope_is_rejected() -> None:
    plan = make_plan([
        step(
            "close_application",
            {"application": "chrome", "scope": "first"},
            "SENSITIVE",
        ),
        step("verify_application_closed", {}, "READ_ONLY"),
    ])

    with pytest.raises(executor.UnsupportedPlan, match="scope"):
        executor.execute_plan(plan)


def youtube_video_plan(query: str = "Big Buck Bunny") -> Plan:
    return make_plan([
        step("play_youtube_video", {"query": query}),
    ])


def test_youtube_video_plan_uses_the_persistent_browser_session(monkeypatch) -> None:
    browser_session = object()
    calls = []
    monkeypatch.setattr(executor, "get_browser_session", lambda: browser_session)
    monkeypatch.setattr(
        executor,
        "play_youtube_video",
        lambda session, query: calls.append((session, query)) or {
            "success": True,
            "title": "Big Buck Bunny - YouTube",
            "url": "https://www.youtube.com/watch?v=test",
            "playing": True,
        },
    )

    result = executor.execute_plan(youtube_video_plan())

    assert calls == [(browser_session, "Big Buck Bunny")]
    assert result == {
        "completed": True,
        "steps": [
            {
                "action": "play_youtube_video",
                "success": True,
                "message": "YouTube video is playing",
            },
        ],
        "video": {
            "success": True,
            "title": "Big Buck Bunny - YouTube",
            "url": "https://www.youtube.com/watch?v=test",
            "playing": True,
        },
    }


def test_youtube_video_failure_returns_a_safe_result(monkeypatch) -> None:
    monkeypatch.setattr(executor, "get_browser_session", lambda: object())

    def fail_to_play(session, query):
        raise RuntimeError("browser details should not reach the user")

    monkeypatch.setattr(executor, "play_youtube_video", fail_to_play)

    result = executor.execute_plan(youtube_video_plan())

    assert result == {
        "completed": False,
        "steps": [
            {
                "action": "play_youtube_video",
                "success": False,
                "message": "Video could not be played or verified",
            },
        ],
    }
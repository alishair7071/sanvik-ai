import pytest
from pydantic import ValidationError

from sanvik_agent.agent.plan import Plan
from sanvik_agent.agent.planner import EmptyTask, plan_task, workflow


VALID_PLAN = {
    "goal": "Open Notepad and type Hello",
    "steps": [
        {
            "action": "open_application",
            "parameters": {"application": "notepad"},
            "expected_result": "Notepad is open",
            "risk_level": "REVERSIBLE",
        },
        {
            "action": "type_text",
            "parameters": {"text": "Hello"},
            "expected_result": "Hello appears in the editor",
            "risk_level": "REVERSIBLE",
        },
        {
            "action": "verify_text",
            "parameters": {"text": "Hello"},
            "expected_result": "Notepad contains Hello",
            "risk_level": "READ_ONLY",
        },
    ],
}


YOUTUBE_VIDEO_PLAN = {
    "goal": "Play Big Buck Bunny on YouTube",
    "steps": [
        {
            "action": "play_youtube_video",
            "parameters": {"query": "Big Buck Bunny"},
            "expected_result": "The requested video is playing",
            "risk_level": "REVERSIBLE",
        },
    ],
}


class FakeChatModel:
    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error
        self.messages = None
        self.schema = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.messages = messages
        if self.error:
            raise self.error
        return self.result


def test_valid_plan_parses() -> None:
    plan = Plan.model_validate(VALID_PLAN)
    assert plan.steps[0].action == "open_application"
    assert plan.steps[1].risk_level == "REVERSIBLE"


@pytest.mark.parametrize(
    "change",
    [
        {"goal": "  "},
        {"steps": []},
        {"steps": [{**VALID_PLAN["steps"][0], "risk_level": "UNKNOWN"}]},
        {"steps": [{**VALID_PLAN["steps"][0], "action": "Open Notepad"}]},
        {"steps": [{**VALID_PLAN["steps"][0], "unexpected": "code"}]},
    ],
)
def test_invalid_plan_rejected(change: dict) -> None:
    with pytest.raises(ValidationError):
        Plan.model_validate({**VALID_PLAN, **change})


def test_graph_calls_model_and_validates_plan(monkeypatch) -> None:
    model = FakeChatModel(VALID_PLAN)
    monkeypatch.setattr("sanvik_agent.agent.planner.get_chat_model", lambda: model)
    result = workflow.invoke({"task": "Open Notepad"})
    assert isinstance(result["plan"], Plan)
    assert model.schema is Plan
    assert model.messages[0][0] == "system"
    assert "Notepad (notepad)" in model.messages[0][1]
    assert "File Explorer (file_explorer)" in model.messages[0][1]
    assert "Google Chrome (chrome)" in model.messages[0][1]
    assert "close_application" in model.messages[0][1]
    assert "verify_application_closed" in model.messages[0][1]
    assert "scope with the exact value all" in model.messages[0][1]
    assert "Do not create a close plan for Notepad" in model.messages[0][1]
    assert model.messages[1] == ("human", "Open Notepad")


def test_graph_creates_a_youtube_video_plan(monkeypatch) -> None:
    model = FakeChatModel(YOUTUBE_VIDEO_PLAN)
    monkeypatch.setattr("sanvik_agent.agent.planner.get_chat_model", lambda: model)

    result = workflow.invoke({"task": "Play Big Buck Bunny on YouTube"})

    assert result["plan"].steps[0].action == "play_youtube_video"
    assert result["plan"].steps[0].parameters == {"query": "Big Buck Bunny"}
    assert "play_youtube_video" in model.messages[0][1]
    assert "parameters must contain only query" in model.messages[0][1]
    assert "Do not mix a YouTube video step with application steps" in model.messages[0][1]


def test_task_is_trimmed_and_default_model_is_selected(monkeypatch) -> None:
    model = FakeChatModel(VALID_PLAN)
    monkeypatch.setattr("sanvik_agent.agent.planner.get_chat_model", lambda: model)
    assert plan_task("  Open Notepad  ").goal == VALID_PLAN["goal"]
    assert model.messages[1] == ("human", "Open Notepad")


def test_empty_task_is_rejected_before_model_call(monkeypatch) -> None:
    model = FakeChatModel(VALID_PLAN)
    monkeypatch.setattr("sanvik_agent.agent.planner.get_chat_model", lambda: model)
    with pytest.raises(EmptyTask):
        plan_task("  ")
    assert model.messages is None


def test_invalid_model_plan_is_rejected(monkeypatch) -> None:
    model = FakeChatModel({"goal": "unsafe", "steps": []})
    monkeypatch.setattr("sanvik_agent.agent.planner.get_chat_model", lambda: model)
    with pytest.raises(ValidationError):
        plan_task("Open Notepad")


def test_model_error_reaches_ipc_error_handler(monkeypatch) -> None:
    model = FakeChatModel(error=RuntimeError("model failed"))
    monkeypatch.setattr("sanvik_agent.agent.planner.get_chat_model", lambda: model)
    with pytest.raises(RuntimeError):
        plan_task("Open Notepad")

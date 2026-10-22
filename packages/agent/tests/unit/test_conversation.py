import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from sanvik_agent.agent import conversation


class FakeChatModel:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []
        self.tools = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        return self.responses.pop(0)


class FakeComputerTool:
    name = "run_known_workflow"

    def __init__(self) -> None:
        self.tasks = []

    def invoke(self, arguments):
        self.tasks.append(arguments["task"])
        return {
            "plan": {"goal": "Open Google Chrome", "steps": []},
            "execution": {"completed": True, "steps": []},
        }


class FakeBrowserTool:
    name = "run_general_browser_task"

    def __init__(self) -> None:
        self.tasks = []

    def invoke(self, arguments):
        self.tasks.append(arguments["task"])
        return {
            "status": "completed",
            "final_result": {
                "success": True,
                "message": "The jobs page is open.",
            },
        }


def new_conversation_id() -> str:
    return str(uuid4())


def test_general_message_returns_direct_answer(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(content="I can help with supported Windows tasks."),
    ])
    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)

    answer = conversation.chat("  What can you do?  ", new_conversation_id())

    assert answer == "I can help with supported Windows tasks."
    assert len(model.calls) == 1
    assert isinstance(model.calls[0][0], SystemMessage)
    assert isinstance(model.calls[0][1], HumanMessage)
    assert model.calls[0][1].content == "What can you do?"


def test_computer_request_runs_tool_then_returns_final_answer(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_known_workflow",
                "args": {"task": "Open Google Chrome."},
                "id": "tool-call-1",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="Chrome opened successfully."),
    ])
    computer_tool = FakeComputerTool()
    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    monkeypatch.setattr(conversation, "run_known_workflow", computer_tool)

    answer = conversation.chat("Could you please get Chrome going for me?", new_conversation_id())

    assert answer == "Task completed successfully."
    assert computer_tool.tasks == ["Open Google Chrome."]
    assert len(model.calls) == 1
    assert model.tools == [computer_tool, conversation.run_general_browser_task]

    system_prompt = model.calls[0][0].content
    assert "clear, self-contained task" in system_prompt
    assert "refined request" in system_prompt



def test_browser_request_runs_general_browser_tool_then_returns_final_answer(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_general_browser_task",
                "args": {"task": "Open the jobs page and search for Python jobs."},
                "id": "tool-call-browser",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="The jobs page is open."),
    ])
    browser_tool = FakeBrowserTool()
    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    monkeypatch.setattr(conversation, "run_general_browser_task", browser_tool)

    answer = conversation.chat(
        "Open a jobs website and search for Python jobs.",
        new_conversation_id(),
    )

    assert answer == "The jobs page is open."
    assert browser_tool.tasks == ["Open the jobs page and search for Python jobs."]
    assert model.tools == [conversation.run_known_workflow, browser_tool]



def test_youtube_request_returns_the_video_execution_result(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_known_workflow",
                "args": {"task": "Play Big Buck Bunny on YouTube."},
                "id": "tool-call-youtube",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="Big Buck Bunny is now playing on YouTube."),
    ])
    tasks = []
    task_result = {
        "plan": {
            "goal": "Play Big Buck Bunny on YouTube",
            "steps": [{"action": "play_youtube_video"}],
        },
        "execution": {
            "completed": True,
            "steps": [{"message": "YouTube video is playing"}],
            "video": {"title": "Big Buck Bunny - YouTube", "playing": True},
        },
    }

    def fake_run_task(task: str) -> dict:
        tasks.append(task)
        return task_result

    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    monkeypatch.setattr("sanvik_agent.tools.known_workflow_tool.run_task", fake_run_task)

    answer = conversation.chat("Play Big Buck Bunny on YouTube", new_conversation_id())

    assert answer == "YouTube video is playing"
    assert tasks == ["Play Big Buck Bunny on YouTube."]


def test_ambiguous_action_returns_clarifying_question(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(content="Which application would you like me to open?"),
    ])
    computer_tool = FakeComputerTool()
    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    monkeypatch.setattr(conversation, "run_known_workflow", computer_tool)

    answer = conversation.chat("Open it", new_conversation_id())

    assert answer == "Which application would you like me to open?"
    assert computer_tool.tasks == []


def test_conversation_remembers_previous_messages(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(content="My name is Sanvik."),
        AIMessage(content="I told you my name is Sanvik."),
    ])
    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    conversation_id = new_conversation_id()

    conversation.chat("What is your name?", conversation_id)
    conversation.chat("What did you just tell me?", conversation_id)

    second_call = model.calls[1]
    assert [message.content for message in second_call[1:]] == [
        "What is your name?",
        "My name is Sanvik.",
        "What did you just tell me?",
    ]


def test_empty_chat_values_are_rejected(monkeypatch) -> None:
    model = FakeChatModel([])
    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)

    with pytest.raises(ValueError, match="Message must not be empty"):
        conversation.chat("   ", new_conversation_id())

    with pytest.raises(ValueError, match="Conversation ID must not be empty"):
        conversation.chat("Hello", "   ")

    assert model.calls == []


def test_model_error_returns_a_safe_conversation_reply(monkeypatch) -> None:
    class BrokenModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            raise RuntimeError("private provider detail")

    monkeypatch.setattr(conversation, "get_chat_model", lambda: BrokenModel())

    answer = conversation.chat("Open Chrome", new_conversation_id())

    assert answer == conversation.PROCESSING_ERROR_MESSAGE
    assert "private provider detail" not in answer


def test_malformed_tool_result_returns_a_safe_conversation_reply(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_known_workflow",
                "args": {"task": "Open Chrome."},
                "id": "tool-call-bad-result",
                "type": "tool_call",
            }],
        ),
    ])

    class MalformedResultTool:
        name = "run_known_workflow"

        def invoke(self, arguments):
            return "not a task result"

    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    monkeypatch.setattr(conversation, "run_known_workflow", MalformedResultTool())

    answer = conversation.chat("Open Chrome", new_conversation_id())

    assert answer == conversation.PROCESSING_ERROR_MESSAGE


def test_tool_error_returns_a_safe_conversation_reply(monkeypatch) -> None:
    model = FakeChatModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_known_workflow",
                "args": {"task": "Open Chrome."},
                "id": "tool-call-error",
                "type": "tool_call",
            }],
        ),
    ])

    class BrokenTool:
        name = "run_known_workflow"

        def invoke(self, arguments):
            raise RuntimeError("private execution detail")

    monkeypatch.setattr(conversation, "get_chat_model", lambda: model)
    monkeypatch.setattr(conversation, "run_known_workflow", BrokenTool())

    answer = conversation.chat("Open Chrome", new_conversation_id())

    assert answer == "The task could not be completed: Task execution failed. Please try again."
    assert "private execution detail" not in answer

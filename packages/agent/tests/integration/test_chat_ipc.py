import json

from sanvik_agent.agent import conversation
from sanvik_agent.ipc.runtime import handle_line


def chat_request(message: str, conversation_id="conversation-1") -> str:
    return json.dumps({
        "version": 1,
        "type": "request",
        "id": "chat-1",
        "payload": {
            "operation": "chat_message",
            "message": message,
            "conversation_id": conversation_id,
        },
    })


def test_chat_message_returns_assistant_reply(monkeypatch) -> None:
    received = []

    def fake_chat(message: str, conversation_id: str) -> str:
        received.append((message, conversation_id))
        return "Chrome opened successfully."

    monkeypatch.setattr(conversation, "chat", fake_chat)

    response, stop = handle_line(chat_request("Open Chrome"))

    assert not stop
    assert received == [("Open Chrome", "conversation-1")]
    assert response["success"] is True
    assert response["payload"]["message"] == "Chrome opened successfully."


def test_chat_message_validates_message_and_conversation_id() -> None:
    response, _ = handle_line(chat_request("   "))
    assert response["error"]["code"] == "invalid_message"

    response, _ = handle_line(chat_request("Hello", ""))
    assert response["error"]["code"] == "invalid_conversation_id"


def test_chat_message_hides_unexpected_errors(monkeypatch) -> None:
    def broken_chat(message: str, conversation_id: str) -> str:
        raise RuntimeError("private detail")

    monkeypatch.setattr(conversation, "chat", broken_chat)

    response, stop = handle_line(chat_request("Hello"))

    assert not stop
    assert response["error"]["code"] == "internal_error"
    assert "private detail" not in response["error"]["message"]

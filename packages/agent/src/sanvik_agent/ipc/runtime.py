"""Line-delimited JSON entry point for the local Tauri process bridge."""

import json
import logging
import sys
from typing import TextIO

from sanvik_agent.execution.plan_validator import UnsupportedPlan
from sanvik_agent.llm.provider import PlanningError

# Protocol settings shared with the Rust bridge.
PROTOCOL_VERSION = 1
logger = logging.getLogger(__name__)



# Build the standard error response sent back to Rust.
def _error(request_id: str | None, code: str, message: str) -> dict:
    return {
        "version": PROTOCOL_VERSION,
        "type": "response",
        "id": request_id,
        "success": False,
        "error": {"code": code, "message": message},
    }



# Handle one request: validate it, run its operation, and build a reply.
def handle_line(line: str) -> tuple[dict, bool]:
    """Process one JSON request and say whether the process should stop."""
    # Part 1: Decode JSON and validate the request envelope.
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        return _error(None, "invalid_json", "Request is not valid JSON"), False

    if not isinstance(request, dict):
        return _error(None, "invalid_request", "Request must be an object"), False

    request_id = request.get("id")
    if not isinstance(request_id, str) or not request_id:
        return _error(None, "invalid_id", "Request ID must be a non-empty string"), False

    # bool is a subclass of int in Python, so require exactly int here.
    if type(request.get("version")) is not int or request["version"] != PROTOCOL_VERSION:
        return _error(request_id, "unsupported_version", "Unsupported protocol version"), False
    if request.get("type") != "request":
        return _error(request_id, "unknown_type", "Expected a request message"), False

    payload = request.get("payload")
    if not isinstance(payload, dict):
        return _error(request_id, "invalid_payload", "Payload must be an object"), False

    # Part 2: Choose the operation requested by Rust.
    operation = payload.get("operation")
    should_stop = False

    if operation == "ping":
        result = {"message": "Sanvik Python runtime is running"}

    elif operation == "echo":
        user_message = payload.get("message")
        if not isinstance(user_message, str) or not user_message.strip():
            return _error(request_id, "invalid_message", "Message must not be empty"), False
        result = {"message": f"Sanvik Python received: {user_message}"}

    elif operation == "chat_message":
        user_message = payload.get("message")
        conversation_id = payload.get("conversation_id")

        if not isinstance(user_message, str) or not user_message.strip():
            return _error(request_id, "invalid_message", "Message must not be empty"), False
        if (
            not isinstance(conversation_id, str)
            or not conversation_id.strip()
            or len(conversation_id) > 128
        ):
            return _error(
                request_id,
                "invalid_conversation_id",
                "Conversation ID must be a non-empty string of at most 128 characters",
            ), False

        try:
            from sanvik_agent.agent.conversation import chat

            result = {"message": chat(user_message, conversation_id)}
        except PlanningError as error:
            return _error(request_id, error.code, error.public_message), False
        except Exception:
            logger.error("chat_failed_unexpected")
            return _error(request_id, "internal_error", "Chat request failed unexpectedly"), False

    elif operation == "run_task":
        # The agent plans and executes; this IPC file only passes in the task.
        task = payload.get("message")
        if not isinstance(task, str) or not task.strip():
            return _error(request_id, "empty_task", "Task must not be empty"), False

        try:
            from sanvik_agent.agent.workflow import run_task

            result = run_task(task)
        except UnsupportedPlan as error:
            return _error(request_id, "unsupported_plan", str(error)), False
        except PlanningError as error:
            return _error(request_id, error.code, error.public_message), False
        except Exception:
            logger.error("execution_failed_unexpected")
            return _error(request_id, "internal_error", "Task failed unexpectedly"), False

    elif operation == "shutdown":
        result = {"message": "Sanvik Python runtime is shutting down"}
        should_stop = True

    else:
        return _error(request_id, "unknown_operation", "Unknown operation"), False

    # Part 3: Wrap the operation result in the shared response format.
    response = {
        "version": PROTOCOL_VERSION,
        "type": "response",
        "id": request_id,
        "success": True,
        "payload": result,
    }
    return response, should_stop



# Keep reading requests from Rust until shutdown or the input pipe closes.
def serve(input_stream: TextIO, output_stream: TextIO) -> None:
    for line in input_stream:
        response, should_stop = handle_line(line)
        output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
        output_stream.flush()
        if should_stop:
            break



# Connect the request loop to the Python process standard input/output.
def main() -> None:
    serve(sys.stdin, sys.stdout)



# Run main only when Rust starts this module as a Python program.
if __name__ == "__main__":
    main()

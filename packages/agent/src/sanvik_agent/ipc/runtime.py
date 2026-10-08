"""Line-delimited JSON entry point for the local Tauri process bridge."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

PROTOCOL_VERSION = 1


def _error(request_id: str | None, code: str, message: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "response",
        "id": request_id,
        "success": False,
        "error": {"code": code, "message": message},
    }


def handle_line(line: str) -> tuple[dict[str, Any], bool]:
    """Return a response and whether the runtime should stop after sending it."""
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        return _error(None, "invalid_json", "Request is not valid JSON"), False

    if not isinstance(request, dict):
        return _error(None, "invalid_request", "Request must be an object"), False

    request_id = request.get("id")
    if not isinstance(request_id, str) or not request_id:
        return _error(None, "invalid_id", "Request ID must be a non-empty string"), False

    if type(request.get("version")) is not int or request["version"] != PROTOCOL_VERSION:
        return _error(request_id, "unsupported_version", "Unsupported protocol version"), False
    if request.get("type") != "request":
        return _error(request_id, "unknown_type", "Expected a request message"), False

    payload = request.get("payload")
    if not isinstance(payload, dict):
        return _error(request_id, "invalid_payload", "Payload must be an object"), False

    operation = payload.get("operation")
    if operation == "ping":
        message = "Sanvik Python runtime is running"
    elif operation == "echo":
        user_message = payload.get("message")
        if not isinstance(user_message, str) or not user_message.strip():
            return _error(request_id, "invalid_message", "Message must not be empty"), False
        message = f"Sanvik Python received: {user_message}"
    elif operation == "shutdown":
        message = "Sanvik Python runtime is shutting down"
    else:
        return _error(request_id, "unknown_operation", "Unknown operation"), False

    return {
        "version": PROTOCOL_VERSION,
        "type": "response",
        "id": request_id,
        "success": True,
        "payload": {"message": message},
    }, operation == "shutdown"


def serve(input_stream: TextIO, output_stream: TextIO) -> None:
    for line in input_stream:
        response, should_stop = handle_line(line)
        output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
        output_stream.flush()
        if should_stop:
            break


def main() -> None:
    serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()

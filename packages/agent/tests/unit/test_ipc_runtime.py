import io
import json

from sanvik_agent.ipc.runtime import handle_line, serve


def test_ping_and_echo_keep_their_ids() -> None:
    output = io.StringIO()
    serve(
        io.StringIO(
            '{"version":1,"type":"request","id":"one","payload":{"operation":"ping"}}\n'
            '{"version":1,"type":"request","id":"two","payload":{"operation":"echo","message":"Hello"}}\n'
        ),
        output,
    )
    first, second = [json.loads(line) for line in output.getvalue().splitlines()]
    assert first["id"] == "one"
    assert first["payload"]["message"] == "Sanvik Python runtime is running"
    assert second["id"] == "two"
    assert second["payload"]["message"] == "Sanvik Python received: Hello"


def test_bad_input_does_not_end_session() -> None:
    response, stop = handle_line("not json")
    assert response["error"]["code"] == "invalid_json"
    assert response["id"] is None
    assert not stop

    response, stop = handle_line('{"version":1,"type":"other","id":"x","payload":{}}')
    assert response["error"]["code"] == "unknown_type"
    assert response["id"] == "x"
    assert not stop


def test_shutdown_acknowledges_and_stops() -> None:
    output = io.StringIO()
    serve(
        io.StringIO(
            '{"version":1,"type":"request","id":"end","payload":{"operation":"shutdown"}}\n'
            '{"version":1,"type":"request","id":"later","payload":{"operation":"ping"}}\n'
        ),
        output,
    )
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(replies) == 1
    assert replies[0]["id"] == "end"


def test_boolean_version_is_rejected() -> None:
    response, stop = handle_line('{"version":true,"type":"request","id":"x","payload":{"operation":"ping"}}')
    assert response["error"]["code"] == "unsupported_version"
    assert not stop

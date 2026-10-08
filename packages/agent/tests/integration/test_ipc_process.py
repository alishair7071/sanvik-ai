import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def request(request_id: str, operation: str, message: str | None = None) -> str:
    payload: dict[str, str] = {"operation": operation}
    if message is not None:
        payload["message"] = message
    return json.dumps(
        {"version": 1, "type": "request", "id": request_id, "payload": payload}
    ) + "\n"


def test_process_handles_multiple_requests_and_shutdown() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    process = subprocess.Popen(
        [sys.executable, "-u", "-m", "sanvik_agent.ipc.runtime"],
        cwd=PACKAGE_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        assert process.stdin is not None
        assert process.stdout is not None
        for item in (
            request("ping-1", "ping"),
            request("echo-2", "echo", "Hello Sanvik"),
            "{not-json}\n",
            request("end-3", "shutdown"),
        ):
            process.stdin.write(item)
            process.stdin.flush()
            reply = json.loads(process.stdout.readline())
            if "ping-1" in item:
                assert reply["id"] == "ping-1"
                assert reply["success"] is True
            elif "echo-2" in item:
                assert reply["id"] == "echo-2"
                assert reply["payload"]["message"] == "Sanvik Python received: Hello Sanvik"
            elif "not-json" in item:
                assert reply["id"] is None
                assert reply["error"]["code"] == "invalid_json"
            else:
                assert reply["id"] == "end-3"
        assert process.wait(timeout=5) == 0
        assert process.stderr is not None
        assert process.stderr.read() == ""
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_process_exits_when_stdin_closes() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    process = subprocess.Popen(
        [sys.executable, "-u", "-m", "sanvik_agent.ipc.runtime"],
        cwd=PACKAGE_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    process.stdin.close()
    assert process.wait(timeout=5) == 0

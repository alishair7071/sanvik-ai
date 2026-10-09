import json

import httpx
import pytest

from sanvik_agent.agent.planning.plan import Plan
from sanvik_agent.models.groq import GroqProvider
from sanvik_agent.models.provider import (
    InvalidModelResponse,
    MissingApiKey,
    ProviderFailure,
    ProviderTimeout,
)

PLAN = {
    "goal": "Open Notepad",
    "steps": [{
        "action": "launch_app",
        "parameters": {"app": "Notepad"},
        "expected_result": "Notepad is open",
        "risk_level": "READ_ONLY",
    }],
}


def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "")
    with pytest.raises(MissingApiKey):
        GroqProvider()



def test_local_env_file_is_used_when_process_env_is_unset(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    import sanvik_agent.models.groq as groq_module

    local_file = tmp_path / ".env"
    local_file.write_text("GROQ_API_KEY=local-test-key\n", encoding="utf-8")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(groq_module, "LOCAL_ENV_FILE", local_file)
    provider = GroqProvider()
    assert provider.api_key == "local-test-key"
def test_structured_request_and_valid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.groq.com/openai/v1/responses"
        assert request.headers["authorization"] == "Bearer test-key"
        data = json.loads(request.content)
        assert data["model"] == "openai/gpt-oss-20b"
        assert data["store"] is False
        assert data["text"]["format"]["type"] == "json_schema"
        assert data["text"]["format"]["strict"] is False
        assert data["input"][1]["content"] == "Open Notepad"
        return httpx.Response(200, json={
            "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(PLAN)}
            ]}],
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = GroqProvider(api_key="test-key", client=client).create_plan("Open Notepad")
    assert isinstance(result, Plan)
    assert result.goal == "Open Notepad"


def test_invalid_model_response() -> None:
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={
            "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"goal":"x","steps":[]}'}
            ]}],
        })
    ))
    with pytest.raises(InvalidModelResponse):
        GroqProvider(api_key="test-key", client=client).create_plan("Open Notepad")


def test_provider_http_error_is_controlled() -> None:
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": "secret"})
    ))
    with pytest.raises(ProviderFailure):
        GroqProvider(api_key="test-key", client=client).create_plan("Open Notepad")


def test_provider_timeout_is_controlled() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderTimeout):
        GroqProvider(api_key="test-key", client=client).create_plan("Open Notepad")
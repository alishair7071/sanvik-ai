import pytest
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

import sanvik_agent.llm.provider as provider_module
from sanvik_agent.agent.plan import Plan
from sanvik_agent.llm.provider import MissingApiKey, UnsupportedProvider, get_chat_model


@pytest.mark.parametrize(
    ("name", "key_name", "model_type"),
    [
        ("groq", "GROQ_API_KEY", ChatGroq),
        ("openai", "OPENAI_API_KEY", ChatOpenAI),
        ("anthropic", "ANTHROPIC_API_KEY", ChatAnthropic),
    ],
)
def test_hardcoded_provider_selects_model(monkeypatch, name, key_name, model_type) -> None:
    monkeypatch.setattr(provider_module, "ACTIVE_PROVIDER", name)
    monkeypatch.setenv(key_name, "test-key")
    model = get_chat_model()
    assert isinstance(model, model_type)
    assert model.with_structured_output(Plan) is not None


def test_selected_provider_requires_its_key(monkeypatch) -> None:
    monkeypatch.setattr(provider_module, "ACTIVE_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(MissingApiKey) as error:
        get_chat_model()
    assert "ANTHROPIC_API_KEY" in error.value.public_message


def test_unsupported_hardcoded_provider_is_clear(monkeypatch) -> None:
    monkeypatch.setattr(provider_module, "ACTIVE_PROVIDER", "unsupported")
    with pytest.raises(UnsupportedProvider):
        get_chat_model()


def test_local_env_and_process_key_override(monkeypatch, tmp_path) -> None:
    local_file = tmp_path / ".env"
    local_file.write_text("GROQ_API_KEY=local-test-key\n", encoding="utf-8")
    monkeypatch.setattr(provider_module, "LOCAL_ENV_FILE", local_file)
    monkeypatch.setattr(provider_module, "ACTIVE_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    model = get_chat_model()
    assert model.groq_api_key.get_secret_value() == "local-test-key"

    monkeypatch.setenv("GROQ_API_KEY", "process-test-key")
    model = get_chat_model()
    assert model.groq_api_key.get_secret_value() == "process-test-key"


def test_other_keys_and_environment_provider_do_not_change_selection(monkeypatch) -> None:
    monkeypatch.setattr(provider_module, "ACTIVE_PROVIDER", "groq")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "another-test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "another-test-key")
    assert isinstance(get_chat_model(), ChatGroq)
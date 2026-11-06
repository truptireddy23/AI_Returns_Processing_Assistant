"""Provider settings and reply parsing for the real model client (M5).

No network: `OpenAIClient` only builds SDK objects here, and the parsing helper
is pure. Covers what an OpenAI-compatible provider such as Groq changes: separate
chat and embedding providers, the old OPENAI_* names, and reasoning-model replies.
"""

from typing import Any

import pytest
from pydantic import SecretStr

from returnguard.config import Settings
from returnguard.pipeline.llm import OpenAIClient, model_client, parse_json_reply


def settings(**overrides: Any) -> Settings:
    """Settings from the process environment only, never app/.env."""
    return Settings(_env_file=None, **overrides)


def test_old_openai_names_still_configure_both_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("CHAT_API_KEY", "EMBEDDING_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-old")
    monkeypatch.setenv("POLICY_MODEL", "gpt-4o-mini")
    s = settings()
    assert s.chat_api_key.get_secret_value() == "sk-old"
    assert s.embedding_api_key.get_secret_value() == "sk-old"
    assert s.chat_model == "gpt-4o-mini"


def test_chat_and_embeddings_can_use_different_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("CHAT_API_KEY", "gsk-groq")
    monkeypatch.setenv("CHAT_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("CHAT_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setenv("CHAT_EXTRA_BODY", '{"reasoning_effort": "none"}')
    monkeypatch.setenv("EMBEDDING_API_KEY", "sk-embed")
    s = settings()
    assert s.chat_api_key.get_secret_value() == "gsk-groq"
    assert s.chat_model == "qwen/qwen3.8-27b"
    assert s.chat_extra_body == {"reasoning_effort": "none"}
    assert s.embedding_api_key.get_secret_value() == "sk-embed"
    assert model_client(s) is not None


@pytest.mark.parametrize(
    ("chat_key", "embedding_key"), [("", ""), ("gsk-groq", ""), ("", "sk-embed")]
)
def test_no_model_client_without_both_providers(chat_key: str, embedding_key: str) -> None:
    s = settings(chat_api_key=SecretStr(chat_key), embedding_api_key=SecretStr(embedding_key))
    assert model_client(s) is None


async def test_calling_an_unconfigured_half_raises_clearly() -> None:
    client = OpenAIClient(chat_api_key="gsk-groq", chat_model="qwen/qwen3.8-27b")
    with pytest.raises(RuntimeError, match="EMBEDDING_API_KEY"):
        await client.embed("hello")


@pytest.mark.parametrize(
    "content",
    [
        '{"authenticity": "unclear"}',
        '<think>The lighting looks off.</think>\n{"authenticity": "unclear"}',
        '```json\n{"authenticity": "unclear"}\n```',
        'Here is my answer: {"authenticity": "unclear"} Hope that helps.',
    ],
)
def test_parse_json_reply_handles_reasoning_model_output(content: str) -> None:
    assert parse_json_reply(content) == {"authenticity": "unclear"}


@pytest.mark.parametrize(
    "content", ["", "not json at all", "[1, 2]", "<think>only thinking</think>"]
)
def test_parse_json_reply_returns_empty_for_anything_else(content: str) -> None:
    assert parse_json_reply(content) == {}

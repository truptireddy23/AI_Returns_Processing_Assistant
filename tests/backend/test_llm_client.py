"""Provider settings and reply parsing for the real model client (M5).

No network: `OpenAIClient` only builds SDK objects here, and the parsing helper
is pure. Covers what an OpenAI-compatible provider such as Groq changes: separate
chat and embedding providers, the old OPENAI_* names, and reasoning-model replies.
"""

import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import SecretStr

from returnguard.config import Settings
from returnguard.pipeline.llm import OpenAIClient, model_client, parse_json_reply
from returnguard.pipeline.retrieval import all_policy_clauses


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


def test_no_model_client_without_a_chat_provider() -> None:
    s = settings(chat_api_key=SecretStr(""), embedding_api_key=SecretStr("sk-embed"))
    assert model_client(s) is None


def test_chat_alone_is_enough_and_embeddings_are_optional() -> None:
    s = settings(chat_api_key=SecretStr("gsk-groq"), embedding_api_key=SecretStr(""))
    client = model_client(s)
    assert client is not None
    assert client.has_embeddings is False
    s = settings(chat_api_key=SecretStr("gsk-groq"), embedding_api_key=SecretStr("sk-embed"))
    assert model_client(s).has_embeddings is True  # type: ignore[union-attr]


def test_a_blank_embedding_dimensions_means_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "")
    assert settings().embedding_dimensions is None


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


async def test_all_policy_clauses_come_back_in_clause_order() -> None:
    @dataclass
    class Chunk:
        clause_id: str

    class FakeDb:
        async def scalars(self, stmt: Any) -> list[Chunk]:
            return [Chunk(c) for c in ("P10", "P2", "P1", "P9")]

    chunks = await all_policy_clauses(FakeDb(), policy_doc_id=uuid.uuid4())  # type: ignore[arg-type]
    assert [c.clause_id for c in chunks] == ["P1", "P2", "P9", "P10"]

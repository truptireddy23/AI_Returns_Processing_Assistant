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


class _RecordingCompletions:
    """Stands in for the SDK's chat.completions: records the request, returns `content`."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        from types import SimpleNamespace

        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(
            model="qwen/qwen3.8-27b",
            choices=[SimpleNamespace(message=message)],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )


def _client_with(content: str) -> tuple[OpenAIClient, _RecordingCompletions]:
    from types import SimpleNamespace

    client = OpenAIClient(chat_api_key="gsk-test", chat_model="qwen/qwen3.8-27b")
    completions = _RecordingCompletions(content)
    client._chat_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))  # type: ignore[assignment]
    return client, completions


async def test_the_reply_cap_is_sent_when_given() -> None:
    """Without a cap Groq budgets 2048 output tokens per call, over its free tier's
    1000 a minute, and refuses every call as "request too large"."""
    client, completions = _client_with('{"veto": false}')

    await client.complete_json(system="s", user="u", max_tokens=200)

    assert completions.kwargs["max_completion_tokens"] == 200


async def test_no_cap_field_is_sent_without_one() -> None:
    client, completions = _client_with('{"veto": false}')

    await client.complete_json(system="s", user="u")

    assert "max_completion_tokens" not in completions.kwargs


async def test_a_reply_cut_off_at_the_cap_fails_closed() -> None:
    client, _ = _client_with('{"product_match": "yes", "authenticity": "gen')

    raw, _usage = await client.complete_json(system="s", user="u", max_tokens=5)

    assert raw == {}


@pytest.mark.parametrize("missing_usage", [False, True])
async def test_policy_tools_are_case_scoped_and_cost_includes_all_rounds(
    missing_usage: bool,
) -> None:
    from decimal import Decimal
    from types import SimpleNamespace

    client = OpenAIClient(
        chat_api_key="test",
        input_usd_per_million=Decimal("1"),
        output_usd_per_million=Decimal("2"),
    )
    requests: list[dict[str, Any]] = []
    executed: list[str] = []

    async def window() -> dict[str, Any]:
        executed.append("window")
        return {"within_window": True}

    async def policy() -> dict[str, Any]:
        executed.append("policy")
        return {"clauses": ["P1"]}

    async def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        if "tools" in kwargs:
            name = kwargs["tools"][0]["function"]["name"]
            call = SimpleNamespace(id=name, function=SimpleNamespace(name=name, arguments="{}"))
            message = SimpleNamespace(
                tool_calls=[call],
                model_dump=lambda **_: {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": name,
                            "type": "function",
                            "function": {"name": name, "arguments": "{}"},
                        }
                    ],
                },
            )
        else:
            message = SimpleNamespace(content='{"eligibility": "eligible"}')
        return SimpleNamespace(
            model="test",
            choices=[SimpleNamespace(message=message)],
            usage=None
            if missing_usage and len(requests) == 1
            else SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    client._chat_client = SimpleNamespace(
        chat=SimpleNamespace(  # type: ignore[assignment]
            completions=SimpleNamespace(create=create)
        )
    )
    raw, usage = await client.policy_with_tools(
        system="Policy",
        user="Return",
        tools={"search_policy": policy, "check_return_window": window},
        max_tokens=300,
    )
    assert raw["eligibility"] == "eligible"
    assert executed == ["policy", "window"]
    assert usage.tokens_in == (20 if missing_usage else 30)
    assert usage.tokens_out == (10 if missing_usage else 15)
    assert usage.usage_complete is (not missing_usage)
    assert usage.cost_usd == (None if missing_usage else Decimal("0.00006"))
    assert len(usage.tool_calls) == 2
    assert requests[-1]["response_format"] == {"type": "json_object"}
    assert sum(m["role"] == "tool" for m in requests[-1]["messages"]) == 2


@pytest.mark.parametrize(
    "name,args", [("delete_return", "{}"), ("search_policy", '{"sql":"DROP"}')]
)
async def test_untrusted_tool_requests_fail_before_execution(name: str, args: str) -> None:
    from types import SimpleNamespace

    client = OpenAIClient(chat_api_key="test")
    executed: list[bool] = []

    async def tool() -> dict[str, Any]:
        executed.append(True)
        return {}

    async def create(**kwargs: Any) -> Any:
        call = SimpleNamespace(id="1", function=SimpleNamespace(name=name, arguments=args))
        return SimpleNamespace(
            usage=None,
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        tool_calls=[call], model_dump=lambda **_: {"role": "assistant"}
                    )
                )
            ],
        )

    client._chat_client = SimpleNamespace(
        chat=SimpleNamespace(  # type: ignore[assignment]
            completions=SimpleNamespace(create=create)
        )
    )
    with pytest.raises(ValueError):
        await client.policy_with_tools(
            system="s",
            user="u",
            max_tokens=100,
            tools={"search_policy": tool, "check_return_window": tool},
        )
    assert not executed


async def test_streaming_assembles_json_accounts_usage_and_closes() -> None:
    from types import SimpleNamespace

    class Stream:
        closed = False

        def __aiter__(self) -> Any:
            async def chunks() -> Any:
                for text in ('{"veto":', "false}"):
                    yield SimpleNamespace(
                        model="test",
                        usage=None,
                        choices=[SimpleNamespace(delta=SimpleNamespace(content=text))],
                    )
                yield SimpleNamespace(
                    model="test",
                    choices=[],
                    usage=SimpleNamespace(prompt_tokens=8, completion_tokens=4),
                )

            return chunks()

        async def close(self) -> None:
            self.closed = True

    stream = Stream()
    requests: list[dict[str, Any]] = []

    async def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        return stream

    client = OpenAIClient(chat_api_key="test", stream_enabled=True)
    client._chat_client = SimpleNamespace(
        chat=SimpleNamespace(  # type: ignore[assignment]
            completions=SimpleNamespace(create=create)
        )
    )
    raw, usage = await client.complete_json(system="s", user="u")
    assert raw == {"veto": False}
    assert usage.stream_chunks == 2 and usage.tokens_in == 8 and usage.tokens_out == 4
    assert requests[0]["stream_options"] == {"include_usage": True}
    assert stream.closed

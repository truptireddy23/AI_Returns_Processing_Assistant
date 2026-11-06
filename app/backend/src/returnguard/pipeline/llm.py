"""The model calls the pipeline needs (M5): one embedding call, one chat call.

Both are `Protocol`s so tests can swap in a fake without the `openai` package ever
being imported. `OpenAIClient` is the only real implementation and speaks the
OpenAI wire format, so any OpenAI-compatible provider (OpenAI, Groq, Gemini, a
local server) is a settings change, not a new client. Chat and embeddings each
have their own key and base URL, since a provider may offer only one of them.
`model_client()` builds it from settings, or returns `None` when either half is
unconfigured, rather than letting `ModelSteps` fail halfway through a review.
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

import structlog

from returnguard.models import EMBEDDING_DIMENSIONS

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

    from returnguard.config import Settings

log = structlog.get_logger(__name__)

# Reasoning models (e.g. Qwen) may put their thinking in the reply as <think>...</think>,
# and some providers wrap JSON in a ```json fence even in JSON mode.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _image_media_type(data: bytes) -> str:
    """Sniffs the format from magic bytes. Customer photos are always re-encoded
    to JPEG before storage (images.py), as are uploaded product reference photos
    (product_photos.py); the auto-generated illustration fallback is PNG
    (generate_product_images.py). Defaults to JPEG rather than guessing wrong."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def parse_json_reply(content: str) -> dict[str, Any]:
    """The reply's JSON object, or `{}` when there isn't one. `{}` fails every
    step's response check, so an unparseable reply is treated like any other
    malformed one (not verified / escalate) instead of crashing the review."""
    text = _THINK_BLOCK.sub("", content).strip()
    fenced = _JSON_FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Last resort: the outermost {...}, for a reply with prose around it.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class ChatUsage:
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


class ChatClient(Protocol):
    async def complete_json(
        self, *, system: str, user: str, images: list[bytes] | None = None
    ) -> tuple[dict[str, Any], ChatUsage]: ...


class OpenAIClient:
    """Real client for any OpenAI-compatible chat and embeddings endpoints.

    Either half may be left unconfigured (no key): calling it then raises clearly.
    `embed_policy` needs only embeddings; `model_client()` requires both.
    """

    def __init__(
        self,
        *,
        chat_api_key: str = "",
        chat_base_url: str = "",
        chat_model: str = "",
        chat_temperature: float = 0.0,
        chat_extra_body: dict[str, Any] | None = None,
        chat_max_retries: int = 2,
        embedding_api_key: str = "",
        embedding_base_url: str = "",
        embedding_model: str = "",
        embedding_dimensions: int | None = None,
    ):
        # Imported here, not at module load: importing this file (e.g. for its
        # Protocols, in tests) must not require the `openai` package to be installed.
        from openai import AsyncOpenAI

        self._chat_client = (
            AsyncOpenAI(
                api_key=chat_api_key,
                base_url=chat_base_url or None,
                max_retries=chat_max_retries,
            )
            if chat_api_key
            else None
        )
        self._embedding_client = (
            AsyncOpenAI(api_key=embedding_api_key, base_url=embedding_base_url or None)
            if embedding_api_key
            else None
        )
        self._chat_model = chat_model
        self._chat_temperature = chat_temperature
        self._chat_extra_body = chat_extra_body or {}
        self._embedding_model = embedding_model
        self._embedding_dimensions = embedding_dimensions

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAIClient:
        return cls(
            chat_api_key=settings.chat_api_key.get_secret_value(),
            chat_base_url=settings.chat_base_url,
            chat_model=settings.chat_model,
            chat_temperature=settings.chat_temperature,
            chat_extra_body=settings.chat_extra_body,
            chat_max_retries=settings.chat_max_retries,
            embedding_api_key=settings.embedding_api_key.get_secret_value(),
            embedding_base_url=settings.embedding_base_url,
            embedding_model=settings.embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
        )

    async def embed(self, text: str) -> list[float]:
        if self._embedding_client is None:
            raise RuntimeError("EMBEDDING_API_KEY (or OPENAI_API_KEY) is not set.")
        extra: dict[str, Any] = (
            {"dimensions": self._embedding_dimensions} if self._embedding_dimensions else {}
        )
        resp = await self._embedding_client.embeddings.create(
            model=self._embedding_model, input=text, **extra
        )
        embedding = list(resp.data[0].embedding)
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"{self._embedding_model} returned {len(embedding)} dimensions; "
                f"policy_chunks.embedding needs {EMBEDDING_DIMENSIONS}. Set "
                "EMBEDDING_DIMENSIONS if the model supports shortening, or use another model."
            )
        return embedding

    async def complete_json(
        self, *, system: str, user: str, images: list[bytes] | None = None
    ) -> tuple[dict[str, Any], ChatUsage]:
        if self._chat_client is None:
            raise RuntimeError("CHAT_API_KEY (or OPENAI_API_KEY) is not set.")
        start = time.monotonic()
        user_content: str | list[dict[str, Any]] = user
        if images:
            user_content = [{"type": "text", "text": user}] + [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{_image_media_type(img)};base64,{base64.b64encode(img).decode()}"
                        )
                    },
                }
                for img in images
            ]
        messages = cast(
            "list[ChatCompletionMessageParam]",
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        resp = await self._chat_client.chat.completions.create(
            model=self._chat_model,
            temperature=self._chat_temperature,
            response_format={"type": "json_object"},
            messages=messages,
            extra_body=self._chat_extra_body or None,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        return (
            parse_json_reply(content),
            ChatUsage(
                model=resp.model,
                tokens_in=usage.prompt_tokens if usage else 0,
                tokens_out=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
            ),
        )


def model_client(settings: Settings) -> OpenAIClient | None:
    """The real client when both chat and embeddings are configured, else `None`
    (callers then run without a model). Policy RAG needs both, so half a
    configuration is logged and treated as none at all."""
    chat_key = settings.chat_api_key.get_secret_value()
    embedding_key = settings.embedding_api_key.get_secret_value()
    if not chat_key and not embedding_key:
        return None
    if not chat_key or not embedding_key:
        log.warning(
            "model_client.incomplete",
            missing="CHAT_API_KEY" if not chat_key else "EMBEDDING_API_KEY",
            effect="running without a model",
        )
        return None
    return OpenAIClient.from_settings(settings)

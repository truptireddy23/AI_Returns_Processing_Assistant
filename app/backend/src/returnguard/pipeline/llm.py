"""The model calls the Policy RAG step needs (M5): one embedding call, one chat call.

Both are `Protocol`s so tests can swap in a fake without the `openai` package ever
being imported, and so a different provider (e.g. an OpenAI-compatible endpoint)
is a `base_url` change, not a new client. `OpenAIClient` is the only real
implementation; it is constructed lazily and raises clearly if no API key is
configured, rather than letting `ModelSteps` silently fall back to guessing.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


def _image_media_type(data: bytes) -> str:
    """Sniffs the format from magic bytes. Customer photos are always re-encoded
    to JPEG before storage (images.py); product reference photos are PNG
    (seed.py). Defaults to JPEG for anything else rather than guessing wrong."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


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
    """Real client: OpenAI, or any OpenAI-compatible chat endpoint via `base_url`.

    Embeddings always go to OpenAI directly (`base_url` only affects chat) since
    `policy_chunks.embedding` is a fixed-dimension column sized for
    `text-embedding-3-small` (`models.EMBEDDING_DIMENSIONS`); swapping embedding
    providers would mean re-embedding every policy chunk, not just a URL change.
    """

    def __init__(
        self,
        *,
        api_key: str,
        chat_base_url: str,
        embedding_model: str,
        chat_model: str,
    ):
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. ModelSteps needs a real model call; "
                "pass steps=RuleSteps() (the default) to run without one."
            )
        # Imported here, not at module load: importing this file (e.g. for its
        # Protocols, in tests) must not require the `openai` package to be installed.
        from openai import AsyncOpenAI

        self._embedding_client = AsyncOpenAI(api_key=api_key)
        self._chat_client = AsyncOpenAI(api_key=api_key, base_url=chat_base_url or None)
        self._embedding_model = embedding_model
        self._chat_model = chat_model

    async def embed(self, text: str) -> list[float]:
        resp = await self._embedding_client.embeddings.create(
            model=self._embedding_model, input=text
        )
        return list(resp.data[0].embedding)

    async def complete_json(
        self, *, system: str, user: str, images: list[bytes] | None = None
    ) -> tuple[dict[str, Any], ChatUsage]:
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
            temperature=0,
            response_format={"type": "json_object"},
            messages=messages,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        content = resp.choices[0].message.content or "{}"
        usage = resp.usage
        return (
            json.loads(content),
            ChatUsage(
                model=resp.model,
                tokens_in=usage.prompt_tokens if usage else 0,
                tokens_out=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
            ),
        )

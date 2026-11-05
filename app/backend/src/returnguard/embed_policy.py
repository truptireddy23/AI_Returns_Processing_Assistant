"""Embeds the active policy's clauses for Policy RAG (M5).

Run with `make embed-policy` (or `uv run python -m returnguard.embed_policy`)
after `make seed` — the seed script creates `policy_docs`/`policy_chunks` rows
with `embedding = NULL`; this fills them in. Safe to re-run: only chunks with
no embedding yet are touched, so it's a no-op once everything is embedded, and
cheap to re-run after `make reset-db`.

Needs `OPENAI_API_KEY` in `app/.env`. Does nothing (and says so) if it isn't set,
rather than failing confusingly partway through.
"""

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import db
from returnguard.config import get_settings
from returnguard.log_config import configure_logging
from returnguard.models import PolicyChunk
from returnguard.pipeline.llm import OpenAIClient

log = structlog.get_logger(__name__)


async def embed_policy_chunks(session: AsyncSession, embedder: OpenAIClient) -> int:
    chunks = list(await session.scalars(select(PolicyChunk).where(PolicyChunk.embedding.is_(None))))
    for chunk in chunks:
        chunk.embedding = await embedder.embed(f"{chunk.title}\n{chunk.body}")
        log.info("embed_policy.chunk", clause_id=chunk.clause_id)
    return len(chunks)


async def _main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    api_key = settings.openai_api_key.get_secret_value()
    if not api_key:
        log.warning("embed_policy.skipped", reason="OPENAI_API_KEY is not set")
        return
    embedder = OpenAIClient(
        api_key=api_key,
        chat_base_url=settings.openai_chat_base_url,
        embedding_model=settings.embedding_model,
        chat_model=settings.policy_model,
    )
    async for session in db.get_session():
        count = await embed_policy_chunks(session, embedder)
        if count:
            await session.commit()
        log.info("embed_policy.done", embedded=count)
    await db.dispose_engine()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()

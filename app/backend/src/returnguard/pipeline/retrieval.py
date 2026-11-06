"""Retrieves the policy clauses relevant to a case (Policy RAG, M5).

Cosine distance over `policy_chunks.embedding` (pgvector), restricted to one
policy document version at a time, so a partially re-embedded new policy
version can never leak a mix of old and new clauses into one decision.

Without an embedding provider configured, `all_policy_clauses` sends the whole
policy instead. The policy is a handful of short clauses, so that costs about as
many tokens as retrieving four, and no clause can be missed.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import PolicyChunk


async def retrieve_policy_clauses(
    db: AsyncSession,
    *,
    query_embedding: list[float],
    policy_doc_id: uuid.UUID,
    k: int = 4,
) -> list[PolicyChunk]:
    """The `k` embedded chunks of `policy_doc_id` closest to `query_embedding`.

    Chunks without an embedding yet (not re-indexed since the last policy
    change — see `embed_policy.py`) are excluded rather than ranked arbitrarily.
    """
    stmt = (
        select(PolicyChunk)
        .where(
            PolicyChunk.policy_doc_id == policy_doc_id,
            PolicyChunk.embedding.is_not(None),
        )
        .order_by(PolicyChunk.embedding.cosine_distance(query_embedding))
        .limit(k)
    )
    return list(await db.scalars(stmt))


async def all_policy_clauses(db: AsyncSession, *, policy_doc_id: uuid.UUID) -> list[PolicyChunk]:
    """Every chunk of `policy_doc_id`, in clause order (P1, P2, ..., P10)."""
    chunks = await db.scalars(select(PolicyChunk).where(PolicyChunk.policy_doc_id == policy_doc_id))
    return sorted(chunks, key=lambda c: (len(c.clause_id), c.clause_id))

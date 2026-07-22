"""Similar-design search — see docs/ai-foundation.md#similar-design-search.

A synchronous read, not a job: it only scans embeddings that are already
computed (cheap arithmetic over already-fetched rows, no provider call, no
network I/O), unlike every other capability in this package. This module
never enqueues anything.

`ai_duplicate_similarity_threshold`-level matches are excluded by design
(see `exclude_design_ids`) so a caller doing "customers who liked this also
liked" doesn't recommend the same design's own near-duplicate back to them.

O(n) full-table scan — acceptable at this phase's expected catalog size (see
docs/ai-foundation.md#similarity-search-is-a-foundation). A future phase
adding pgvector or a real ANN index only needs to change this one function.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ai import DesignEmbedding

from .local_provider import cosine_similarity


def find_similar_designs(
    db: Session,
    *,
    design_id: uuid.UUID,
    limit: int = 10,
    exclude_design_ids: frozenset[uuid.UUID] = frozenset(),
) -> list[tuple[uuid.UUID, float]]:
    source = db.execute(
        select(DesignEmbedding).where(DesignEmbedding.design_id == design_id)
    ).scalar_one_or_none()
    if source is None:
        return []

    source_vector = tuple(source.embedding)
    excluded = exclude_design_ids | {design_id}

    others = (
        db.execute(select(DesignEmbedding).where(DesignEmbedding.design_id.not_in(excluded)))
        .scalars()
        .all()
    )

    scored = [
        (other.design_id, cosine_similarity(source_vector, tuple(other.embedding)))
        for other in others
        if other.dimension == source.dimension
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]

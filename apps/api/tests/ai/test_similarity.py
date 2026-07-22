"""Similar-design search — see docs/ai-foundation.md#similar-design-search.
A synchronous read over existing embeddings; no jobs involved."""

from sqlalchemy.orm import Session

from app.services.ai.similarity import find_similar_designs
from tests.db.factories import make_design, make_design_embedding


def test_find_similar_designs_orders_by_descending_similarity(db_session: Session) -> None:
    source = make_design(db_session)
    close = make_design(db_session)
    far = make_design(db_session)

    make_design_embedding(db_session, design=source, embedding=[1.0, 0.0, 0.0, 0.0])
    make_design_embedding(db_session, design=close, embedding=[0.9, 0.1, 0.0, 0.0])
    make_design_embedding(db_session, design=far, embedding=[0.0, 0.0, 1.0, 0.0])
    db_session.commit()

    results = find_similar_designs(db_session, design_id=source.id, limit=10)

    assert [design_id for design_id, _ in results] == [close.id, far.id]
    assert results[0][1] > results[1][1]


def test_find_similar_designs_excludes_the_source_design(db_session: Session) -> None:
    source = make_design(db_session)
    make_design_embedding(db_session, design=source, embedding=[1.0, 0.0])
    db_session.commit()

    results = find_similar_designs(db_session, design_id=source.id, limit=10)

    assert results == []


def test_find_similar_designs_respects_the_exclude_set(db_session: Session) -> None:
    source = make_design(db_session)
    excluded = make_design(db_session)
    included = make_design(db_session)

    make_design_embedding(db_session, design=source, embedding=[1.0, 0.0])
    make_design_embedding(db_session, design=excluded, embedding=[0.99, 0.01])
    make_design_embedding(db_session, design=included, embedding=[0.9, 0.1])
    db_session.commit()

    results = find_similar_designs(
        db_session, design_id=source.id, limit=10, exclude_design_ids=frozenset({excluded.id})
    )

    assert [design_id for design_id, _ in results] == [included.id]


def test_find_similar_designs_returns_empty_when_source_has_no_embedding(
    db_session: Session,
) -> None:
    source = make_design(db_session)
    other = make_design(db_session)
    make_design_embedding(db_session, design=other, embedding=[1.0, 0.0])
    db_session.commit()

    assert find_similar_designs(db_session, design_id=source.id, limit=10) == []


def test_find_similar_designs_respects_limit(db_session: Session) -> None:
    source = make_design(db_session)
    make_design_embedding(db_session, design=source, embedding=[1.0, 0.0])
    for _ in range(5):
        other = make_design(db_session)
        make_design_embedding(db_session, design=other, embedding=[0.8, 0.2])
    db_session.commit()

    results = find_similar_designs(db_session, design_id=source.id, limit=2)

    assert len(results) == 2

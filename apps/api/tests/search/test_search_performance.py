"""Performance tests for design search over a representative-sized dataset.

15k rows with a 200+ word shared vocabulary keeps keyword match selectivity
realistic (a handful of percent, not "half the table") — that's what makes
the planner actually reach for the GIN index instead of a sequential scan
(verified empirically; a small, low-cardinality vocabulary makes Postgres
correctly prefer a seq scan instead, which is *not* a bug, just not
representative of a real catalog).

Note: `test_keyword_search_uses_the_gin_index_at_scale` asserts on the query
planner's *choice*, which is cost-estimate-based and therefore not perfectly
deterministic — `ANALYZE` computes its statistics from a random sample, so on
a rare run its estimate can land close enough to the seq-scan/index-scan
boundary to flip either way. This has been observed as an occasional flake
in a full test-suite run (never in isolation). A larger row count was tried
to widen the margin, but at 40k rows the bulk insert (GIN index maintenance
on every row) made the whole file dramatically slower and, empirically, no
more reliable — so this stays at the original, well-tested 15k rather than
trade a rare flake for a consistently slow suite.
"""

import random
import time
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.db.models.design import Design
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user

_ROW_COUNT = 15_000
_VOCABULARY = [f"filler{i}" for i in range(200)] + ["bridal", "henna", "mehndi", "wedding"]
_LATENCY_BUDGET_SECONDS = 1.5


def _bulk_insert_designs(db_session: Session, count: int) -> None:
    rng = random.Random(42)
    rows = [
        {
            "id": uuid.uuid4(),
            "title": " ".join(rng.choices(_VOCABULARY, k=4)),
            "description": " ".join(rng.choices(_VOCABULARY, k=8)),
            "status": "published",
            "view_count": rng.randint(0, 10_000),
            "save_count": rng.randint(0, 1_000),
        }
        for _ in range(count)
    ]
    db_session.execute(insert(Design), rows)
    db_session.execute(text("ANALYZE designs"))


def test_keyword_search_uses_the_gin_index_at_scale(db_session: Session) -> None:
    _bulk_insert_designs(db_session, _ROW_COUNT)

    plan = (
        db_session.execute(
            text(
                """
                EXPLAIN
                SELECT id FROM designs
                WHERE status = 'published' AND deleted_at IS NULL
                  AND search_vector @@ websearch_to_tsquery('english', :q)
                ORDER BY ts_rank(search_vector, websearch_to_tsquery('english', :q)) DESC, id DESC
                LIMIT 21
                """
            ),
            {"q": "bridal wedding"},
        )
        .scalars()
        .all()
    )
    plan_text = "\n".join(plan)

    assert "Seq Scan on designs" not in plan_text
    assert "ix_designs_search_vector" in plan_text


def test_keyword_search_endpoint_stays_within_latency_budget_at_scale(
    client: TestClient, db_session: Session
) -> None:
    _bulk_insert_designs(db_session, _ROW_COUNT)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    started = time.perf_counter()
    response = client.get(
        "/api/v1/designs/search",
        params={"q": "bridal wedding", "sort": "relevance", "limit": 20},
        headers=auth_headers(token),
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert len(response.json()["items"]) > 0
    assert elapsed < _LATENCY_BUDGET_SECONDS


def test_filtered_pagination_stays_within_latency_budget_at_scale(
    client: TestClient, db_session: Session
) -> None:
    _bulk_insert_designs(db_session, _ROW_COUNT)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    cursor: str | None = None
    for _ in range(5):
        params: dict[str, object] = {"sort": "popular", "limit": 20}
        if cursor is not None:
            params["cursor"] = cursor
        started = time.perf_counter()
        response = client.get("/api/v1/designs/search", params=params, headers=auth_headers(token))
        elapsed = time.perf_counter() - started

        assert response.status_code == 200
        assert elapsed < _LATENCY_BUDGET_SECONDS
        body = response.json()
        if not body["page_info"]["has_more"]:
            break
        cursor = body["page_info"]["next_cursor"]


def test_suggestions_endpoint_stays_within_latency_budget_at_scale(
    client: TestClient, db_session: Session
) -> None:
    _bulk_insert_designs(db_session, _ROW_COUNT)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    started = time.perf_counter()
    response = client.get(
        "/api/v1/designs/search/suggestions",
        params={"q": "brid"},
        headers=auth_headers(token),
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < _LATENCY_BUDGET_SECONDS

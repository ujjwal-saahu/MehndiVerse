"""Retrieval-quality evaluation for the local heuristic embedding provider —
see docs/ai-foundation.md#retrieval-quality-evaluation.

This is a small, hand-built, fully documented synthetic dataset (not a
real photo corpus, which this environment has no access to): nine
64x64 solid-swatch images spanning three "families" (red, gold, blue),
three shades apiece. `LocalHeuristicProvider.generate_embedding` is a
perceptual-hash-style heuristic (grayscale + color downsampling — see
`app/services/ai/local_provider.py`'s module docstring for the exact
method), so the one property it should reliably deliver is: for a given
query image, other images from the *same color family* should rank above
images from a *different* family. That is exactly what recall@k over this
dataset measures below.

Dataset (documented here so the assertion is legible from the test alone):
    red family:  RED_DEEP (150,20,20), RED_BRIGHT (200,30,30), RED_LIGHT (230,90,90)
    gold family: GOLD_DEEP (180,140,30), GOLD_BRIGHT (212,175,55), GOLD_LIGHT (235,210,140)
    blue family: BLUE_DEEP (20,50,140), BLUE_BRIGHT (40,90,190), BLUE_LIGHT (110,150,230)

For each of the 9 images used as a query, its 2 same-family peers are the
"relevant" set (8 candidates considered per query, since the query itself
is excluded from its own results). recall@2 = (relevant items found in the
top 2 results) / 2, averaged over all 9 queries.
"""

from sqlalchemy.orm import Session

from app.services.ai.local_provider import LocalHeuristicProvider
from app.services.ai.similarity import find_similar_designs
from tests.ai.conftest import make_test_image_bytes
from tests.db.factories import make_design, make_design_embedding

# name -> (family, RGB)
_DATASET: dict[str, tuple[str, tuple[int, int, int]]] = {
    "RED_DEEP": ("red", (150, 20, 20)),
    "RED_BRIGHT": ("red", (200, 30, 30)),
    "RED_LIGHT": ("red", (230, 90, 90)),
    "GOLD_DEEP": ("gold", (180, 140, 30)),
    "GOLD_BRIGHT": ("gold", (212, 175, 55)),
    "GOLD_LIGHT": ("gold", (235, 210, 140)),
    "BLUE_DEEP": ("blue", (20, 50, 140)),
    "BLUE_BRIGHT": ("blue", (40, 90, 190)),
    "BLUE_LIGHT": ("blue", (110, 150, 230)),
}

# The minimum acceptable mean recall@2 across the whole dataset. Documented,
# not tuned to whatever the code happens to currently produce: 0.7 means
# "the average query finds at least 1.4 of its 2 same-family peers in its
# top 2 results," a low bar deliberately set well under what a perceptual-
# hash-style color heuristic should trivially achieve on solid swatches —
# this guards against a regression that breaks similarity ranking entirely,
# not a benchmark of state-of-the-art retrieval quality.
_MIN_MEAN_RECALL_AT_2 = 0.7


def test_local_provider_retrieval_quality_recall_at_2(db_session: Session) -> None:
    provider = LocalHeuristicProvider()
    design_id_by_name: dict[str, object] = {}
    family_by_design_id: dict[object, str] = {}

    for name, (family, rgb) in _DATASET.items():
        design = make_design(db_session)
        embedding_result = provider.generate_embedding(image_bytes=make_test_image_bytes(color=rgb))
        make_design_embedding(
            db_session,
            design=design,
            embedding=list(embedding_result.vector),
            provider=embedding_result.provider,
            model_name=embedding_result.model,
        )
        design_id_by_name[name] = design.id
        family_by_design_id[design.id] = family
    db_session.commit()

    recalls: list[float] = []
    for name in _DATASET:
        query_design_id = design_id_by_name[name]
        query_family = family_by_design_id[query_design_id]
        relevant_count = (
            sum(1 for other_name, (family, _) in _DATASET.items() if family == query_family) - 1
        )  # exclude the query itself

        top_k = find_similar_designs(db_session, design_id=query_design_id, limit=2)
        hits = sum(1 for matched_id, _ in top_k if family_by_design_id[matched_id] == query_family)
        recalls.append(hits / relevant_count)

    mean_recall = sum(recalls) / len(recalls)
    assert mean_recall >= _MIN_MEAN_RECALL_AT_2, (
        f"Mean recall@2 across the {len(_DATASET)}-image documented dataset was "
        f"{mean_recall:.2f}, below the minimum acceptable {_MIN_MEAN_RECALL_AT_2} — "
        "similar-design ranking has regressed."
    )

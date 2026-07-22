"""`LocalHeuristicProvider` — see docs/ai-foundation.md#local-heuristic-
provider. Pure computation, no DB/network needed."""

import io

from PIL import Image

from app.services.ai.local_provider import LocalHeuristicProvider, cosine_similarity
from tests.ai.conftest import make_test_image_bytes

provider = LocalHeuristicProvider()


def test_embedding_is_deterministic_for_the_same_image() -> None:
    image_bytes = make_test_image_bytes(color=(200, 30, 30))
    first = provider.generate_embedding(image_bytes=image_bytes)
    second = provider.generate_embedding(image_bytes=image_bytes)
    assert first.vector == second.vector
    assert first.dimension == len(first.vector) == 112


def test_identical_images_are_maximally_similar() -> None:
    image_bytes = make_test_image_bytes(color=(20, 140, 70))
    result = provider.generate_embedding(image_bytes=image_bytes)
    similarity = cosine_similarity(result.vector, result.vector)
    assert similarity == 1.0


def test_different_colored_images_are_less_similar_than_identical_ones() -> None:
    red = provider.generate_embedding(image_bytes=make_test_image_bytes(color=(200, 30, 30)))
    blue = provider.generate_embedding(image_bytes=make_test_image_bytes(color=(40, 90, 190)))
    cross_similarity = cosine_similarity(red.vector, blue.vector)
    assert cross_similarity < 1.0


def test_cosine_similarity_rejects_mismatched_dimensions() -> None:
    try:
        cosine_similarity((1.0, 2.0), (1.0, 2.0, 3.0))
    except ValueError:
        return
    raise AssertionError("Expected a ValueError for mismatched vector dimensions.")


def test_cosine_similarity_of_zero_vector_is_zero() -> None:
    assert cosine_similarity((0.0, 0.0), (1.0, 1.0)) == 0.0


def test_suggest_tags_detects_a_known_color() -> None:
    gold_bytes = make_test_image_bytes(color=(212, 175, 55))
    result = provider.suggest_tags(image_bytes=gold_bytes)
    tag_names = {name for name, _ in result.tags}
    assert "gold" in tag_names


def test_suggest_tags_excludes_already_applied_tags() -> None:
    gold_bytes = make_test_image_bytes(color=(212, 175, 55))
    result = provider.suggest_tags(image_bytes=gold_bytes, existing_tags=("gold",))
    tag_names = {name for name, _ in result.tags}
    assert "gold" not in tag_names


def test_suggest_tags_ranks_by_descending_confidence() -> None:
    result = provider.suggest_tags(image_bytes=make_test_image_bytes())
    confidences = [confidence for _, confidence in result.tags]
    assert confidences == sorted(confidences, reverse=True)


def test_moderate_image_flags_a_tiny_low_variance_image() -> None:
    tiny_solid = make_test_image_bytes(size=(10, 10), color=(128, 128, 128))
    result = provider.moderate_image(image_bytes=tiny_solid)
    assert result.is_flagged is True
    assert "low_resolution" in result.categories


def test_moderate_image_does_not_flag_a_normal_sized_varied_image() -> None:
    # A checkerboard has real pixel-to-pixel variance, unlike a solid fill.
    image = Image.new("RGB", (200, 200))
    pixels = image.load()
    for x in range(200):
        for y in range(200):
            pixels[x, y] = (255, 255, 255) if (x // 10 + y // 10) % 2 == 0 else (0, 0, 0)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    result = provider.moderate_image(image_bytes=buffer.getvalue())
    assert result.is_flagged is False

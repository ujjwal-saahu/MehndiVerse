"""`LocalHeuristicProvider.generate_design_image` — see
docs/ai-design-assistant.md#provider-abstraction. Pure computation, no DB/
network needed."""

from app.services.ai.local_provider import LocalHeuristicProvider

provider = LocalHeuristicProvider()


def test_generate_design_image_is_deterministic_for_the_same_prompt() -> None:
    first = provider.generate_design_image(prompt="bold Arabic mandala for a wedding, hand")
    second = provider.generate_design_image(prompt="bold Arabic mandala for a wedding, hand")
    assert first.image_bytes == second.image_bytes


def test_generate_design_image_varies_with_the_prompt() -> None:
    first = provider.generate_design_image(prompt="bold Arabic mandala for a wedding, hand")
    second = provider.generate_design_image(prompt="delicate floral design for engagement, foot")
    assert first.image_bytes != second.image_bytes


def test_generate_design_image_returns_valid_metadata() -> None:
    result = provider.generate_design_image(prompt="minimalist geometric design")
    assert result.provider == "local"
    assert result.content_type == "image/png"
    assert result.width > 0
    assert result.height > 0
    assert result.cost_usd == 0.0
    assert len(result.image_bytes) > 0


def test_generate_design_image_ignores_allow_training_flag_but_accepts_it() -> None:
    # The local provider has nothing to honor `allow_training` with, but the
    # call must not raise either way — see docs/ai-design-assistant.md
    # #consent-for-provider-training.
    result_a = provider.generate_design_image(prompt="peacock motif", allow_training=False)
    result_b = provider.generate_design_image(prompt="peacock motif", allow_training=True)
    assert result_a.image_bytes == result_b.image_bytes

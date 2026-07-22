"""Optional sandbox test — exercises the *actually configured* AI provider
(`app.services.ai.factory.get_ai_provider()`), not a mock/fake, through one
real `generate_design_image` + `moderate_image` round trip.

Skipped by default: this environment has no real cloud AI provider
credentials configured (`ai_provider` defaults to `"local"`, which needs no
network access at all), and CI should never depend on an external
provider's uptime or spend real API credits on every run. Opt in with:

    AI_SANDBOX_TESTS=1 pytest tests/ai/test_design_generation_sandbox.py

In a deployment where `ai_provider` is set to a real cloud provider (with
its own sandbox/test-mode credentials — see docs/ai-design-assistant.md
#provider-abstraction), this same test exercises that provider's real
sandbox API end-to-end, proving the `AiProvider` abstraction actually holds
up against something other than the local heuristic implementation.
"""

import os

import pytest

from app.services.ai.design_generation import build_prompt
from app.services.ai.factory import get_ai_provider

pytestmark = pytest.mark.skipif(
    os.environ.get("AI_SANDBOX_TESTS") != "1",
    reason="Optional sandbox test — set AI_SANDBOX_TESTS=1 to run against the configured "
    "AiProvider (whatever app.core.config.Settings.ai_provider currently points to).",
)


def test_configured_provider_generates_and_moderates_a_real_result() -> None:
    provider = get_ai_provider()
    prompt = build_prompt(
        style="Arabic",
        occasion="wedding",
        body_placement="hand",
        difficulty_level="intermediate",
        density="bold",
        is_symmetric=True,
        pattern_elements=["peacock", "paisley"],
        theme="royal",
        personalization_text=None,
        additional_instructions=None,
    )

    result = provider.generate_design_image(prompt=prompt, allow_training=False)
    assert result.image_bytes
    assert result.width > 0
    assert result.height > 0
    assert result.cost_usd >= 0.0

    moderation = provider.moderate_image(image_bytes=result.image_bytes)
    assert 0.0 <= moderation.confidence <= 1.0

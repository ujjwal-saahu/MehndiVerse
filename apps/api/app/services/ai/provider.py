"""AI-provider abstraction — see docs/ai-foundation.md#provider-abstraction.

Mirrors `app/services/payments/base.py` and `app/services/search/base.py`
exactly: an ABC plus frozen dataclasses describing normalized results, so
every capability module in this package (tagging, embeddings, moderation)
depends only on this interface — never on a specific provider's SDK or
response shape. `app/services/ai/factory.py::get_ai_provider()` is the only
place that picks a concrete implementation.

Every method takes raw image *bytes*, not a URL — fetching the bytes (a
network operation, see `app/services/ai/imaging.py`) is the caller's job,
kept separate from computing on them (pure, deterministic, trivially
testable without mocking any I/O).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TagSuggestionResult:
    provider: str
    model: str
    # (tag_name, confidence 0..1), highest confidence first.
    tags: tuple[tuple[str, float], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EmbeddingResult:
    provider: str
    model: str
    vector: tuple[float, ...]

    @property
    def dimension(self) -> int:
        return len(self.vector)


@dataclass(frozen=True)
class ModerationResult:
    provider: str
    model: str
    is_flagged: bool
    confidence: float
    categories: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DesignImageResult:
    """The output of a personalized design-generation call — see
    docs/ai-design-assistant.md#provider-abstraction. `cost_usd` is always
    populated (`0.0` for a provider with no real per-call cost, like the
    local heuristic one) rather than left `None`, so cost/usage reporting
    (docs/ai-design-assistant.md#record-cost-and-usage-metadata) never has
    to special-case "provider didn't say" — see
    docs/ai-foundation.md#never-expose-provider-keys for why nothing here is
    ever a credential."""

    provider: str
    model: str
    image_bytes: bytes
    content_type: str
    width: int
    height: int
    cost_usd: float = 0.0


class AiProvider(ABC):
    """Every implementation must set `name` and never accept or return a
    credential — see docs/ai-foundation.md#never-expose-provider-keys. A
    provider that talks to a real external API keeps its key entirely
    inside its own module (read from `app/core/config.py` at construction
    time), the same way `RazorpayProvider` does."""

    name: str

    @abstractmethod
    def suggest_tags(
        self, *, image_bytes: bytes, existing_tags: tuple[str, ...] = ()
    ) -> TagSuggestionResult: ...

    @abstractmethod
    def generate_embedding(self, *, image_bytes: bytes) -> EmbeddingResult: ...

    @abstractmethod
    def moderate_image(self, *, image_bytes: bytes) -> ModerationResult: ...

    @abstractmethod
    def generate_design_image(
        self, *, prompt: str, allow_training: bool = False
    ) -> DesignImageResult:
        """Personalized mehndi-design generation from a constructed text
        prompt — see docs/ai-design-assistant.md#prompt-construction.
        `allow_training` mirrors the caller's explicit consent decision (see
        docs/ai-design-assistant.md#consent-for-provider-training) verbatim;
        a real cloud provider implementation is the only place that consent
        flag can actually be honored (e.g. passed through as an API
        parameter that opts an image out of a training dataset) — the
        abstraction exists precisely so that decision is never lost between
        the caller and the provider."""
        ...

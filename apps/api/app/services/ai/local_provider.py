"""`LocalHeuristicProvider` — a real, deterministic, dependency-light
`AiProvider` implementation that runs entirely on-process (no network call,
no API key) — see docs/ai-foundation.md#local-heuristic-provider.

This is the same "sandbox/foundation, not production-grade" precedent
`app/services/payments/razorpay_provider.py` and
`app/services/search/postgres_provider.py` set: a real, working
implementation behind the `AiProvider` interface, honest about its limits
(perceptual-hash-style embeddings and hand-picked heuristics, not a trained
model), swappable for a real cloud AI provider later purely by adding a new
module and a factory branch — no caller changes.

Every method here is pure and synchronous (Pillow decode + arithmetic),
which is exactly why the background-job layer (app/services/ai/jobs.py)
still wraps calls into it with a timeout: a corrupt or adversarially large
image can make Pillow itself hang or run far longer than expected, and the
job layer must not trust that any provider — including this one — is
always fast.
"""

import hashlib
import io
import math
import random

from PIL import Image, ImageDraw

from .provider import (
    AiProvider,
    DesignImageResult,
    EmbeddingResult,
    ModerationResult,
    TagSuggestionResult,
)

MODEL_NAME = "local-heuristic-v1"

# --- Design-image generation (Phase 21) -------------------------------------
#
# A deterministic, dependency-light stand-in for a real text-to-image model:
# renders a radial henna-style motif (concentric "petal" arcs around a
# center point) whose petal count/size/stroke color are derived from a hash
# of the prompt, so the same prompt always produces the same image (useful
# for tests) while different prompts visibly differ. This is honestly not a
# generative model — see docs/ai-design-assistant.md#provider-abstraction —
# but it is a real rendering, not a fixed placeholder image.
_DESIGN_IMAGE_SIZE = 512
_DESIGN_BACKGROUND = (250, 240, 222)  # cream, mirrors a henna-paste-on-skin canvas
_DESIGN_STROKE_PALETTE: tuple[tuple[int, int, int], ...] = (
    (101, 67, 33),  # henna brown
    (91, 46, 16),
    (128, 76, 33),
)

_EMBEDDING_GRAY_SIZE = 8  # 8x8 grayscale grid
_EMBEDDING_COLOR_SIZE = 4  # 4x4 RGB grid
_EMBEDDING_DIMENSION = (_EMBEDDING_GRAY_SIZE**2) + (_EMBEDDING_COLOR_SIZE**2 * 3)

# Named color buckets tag suggestion classifies the image's average color
# against — deliberately small and mehndi-catalog-relevant, not a general
# color taxonomy.
_COLOR_BUCKETS: dict[str, tuple[int, int, int]] = {
    "black": (20, 20, 20),
    "brown": (101, 67, 33),
    "red": (200, 30, 30),
    "orange": (230, 120, 30),
    "gold": (212, 175, 55),
    "cream": (245, 235, 210),
    "white": (250, 250, 250),
    "gray": (140, 140, 140),
    "green": (40, 140, 70),
    "blue": (40, 90, 190),
    "pink": (230, 120, 160),
    "purple": (120, 60, 160),
}
_MAX_COLOR_DISTANCE = math.sqrt(3 * 255**2)

# Moderation calibration — real photographs have substantial pixel-to-pixel
# variance; a near-blank/solid-color image (a common signature of a broken
# upload, a placeholder, or an unrelated screenshot) does not. This is a
# pre-filter heuristic, not a content classifier — see
# docs/ai-foundation.md#moderation-hooks-are-a-heuristic-foundation.
_EXPECTED_STDDEV = 40.0
_MIN_DIMENSION = 100


def _decode(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes))


def _grayscale_stddev(image: Image.Image) -> float:
    histogram = image.convert("L").histogram()
    total = sum(histogram)
    if total == 0:
        return 0.0
    mean = sum(value * count for value, count in enumerate(histogram)) / total
    variance = sum(((value - mean) ** 2) * count for value, count in enumerate(histogram)) / total
    return math.sqrt(variance)


def _render_design_image(prompt: str) -> Image.Image:
    """Pure function of `prompt` -> a deterministic radial henna-motif
    image. See this module's "Design-image generation" section docstring
    above for what this is and isn't."""
    seed = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)

    size = _DESIGN_IMAGE_SIZE
    center = size / 2
    image = Image.new("RGB", (size, size), color=_DESIGN_BACKGROUND)
    draw = ImageDraw.Draw(image)

    petal_count = rng.randint(8, 16)
    ring_count = rng.randint(2, 4)
    max_radius = size * 0.42

    for ring in range(ring_count):
        ring_radius = max_radius * (ring + 1) / ring_count
        stroke = _DESIGN_STROKE_PALETTE[ring % len(_DESIGN_STROKE_PALETTE)]
        stroke_width = max(1, 4 - ring)
        for petal in range(petal_count):
            angle = (2 * math.pi * petal / petal_count) + (ring * 0.15)
            petal_length = ring_radius * rng.uniform(0.7, 1.0)
            tip_x = center + petal_length * math.cos(angle)
            tip_y = center + petal_length * math.sin(angle)
            base_radius = ring_radius * 0.4
            base_x = center + base_radius * math.cos(angle)
            base_y = center + base_radius * math.sin(angle)
            draw.line([(base_x, base_y), (tip_x, tip_y)], fill=stroke, width=stroke_width)
            draw.ellipse(
                [tip_x - 4, tip_y - 4, tip_x + 4, tip_y + 4],
                outline=stroke,
                width=stroke_width,
            )

    draw.ellipse(
        [center - 10, center - 10, center + 10, center + 10],
        fill=_DESIGN_STROKE_PALETTE[0],
    )
    return image


def _nearest_color_bucket(rgb: tuple[float, float, float]) -> tuple[str, float]:
    best_name = "gray"
    best_distance = _MAX_COLOR_DISTANCE
    for name, bucket_rgb in _COLOR_BUCKETS.items():
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb, bucket_rgb, strict=True)))
        if distance < best_distance:
            best_distance = distance
            best_name = name
    confidence = max(0.0, 1.0 - (best_distance / _MAX_COLOR_DISTANCE))
    return best_name, confidence


class LocalHeuristicProvider(AiProvider):
    name = "local"

    def generate_embedding(self, *, image_bytes: bytes) -> EmbeddingResult:
        # `.tobytes()` (typed as `bytes`, genuinely iterable) rather than
        # `.getdata()` (Pillow's stub types it as `ImagingCore`, which is
        # missing `__iter__` in the shipped stub even though it iterates
        # fine at runtime) -- for "L"/"RGB" mode this is the same flattened,
        # unpadded pixel order `.getdata()` would give.
        image = _decode(image_bytes)
        gray = image.convert("L").resize(
            (_EMBEDDING_GRAY_SIZE, _EMBEDDING_GRAY_SIZE), Image.Resampling.LANCZOS
        )
        gray_vector = [value / 255.0 for value in gray.tobytes()]

        color = image.convert("RGB").resize(
            (_EMBEDDING_COLOR_SIZE, _EMBEDDING_COLOR_SIZE), Image.Resampling.LANCZOS
        )
        color_vector = [channel / 255.0 for channel in color.tobytes()]

        vector = tuple(gray_vector + color_vector)
        return EmbeddingResult(provider=self.name, model=MODEL_NAME, vector=vector)

    def suggest_tags(
        self, *, image_bytes: bytes, existing_tags: tuple[str, ...] = ()
    ) -> TagSuggestionResult:
        image = _decode(image_bytes).convert("RGB")
        small = image.resize((32, 32), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())
        avg_rgb = (
            sum(p[0] for p in pixels) / len(pixels),
            sum(p[1] for p in pixels) / len(pixels),
            sum(p[2] for p in pixels) / len(pixels),
        )
        color_tag, color_confidence = _nearest_color_bucket(avg_rgb)

        width, height = image.size
        if width > height * 1.15:
            orientation_tag, orientation = "landscape", width / max(height, 1)
        elif height > width * 1.15:
            orientation_tag, orientation = "portrait", height / max(width, 1)
        else:
            orientation_tag, orientation = "square", 1.0
        orientation_confidence = min(1.0, 0.6 + (abs(orientation - 1.0) * 0.2))

        stddev = _grayscale_stddev(image)
        density_tag = "bold" if stddev > _EXPECTED_STDDEV else "delicate"
        density_confidence = min(1.0, abs(stddev - _EXPECTED_STDDEV) / _EXPECTED_STDDEV + 0.5)

        existing = {t.lower() for t in existing_tags}
        candidates = [
            (color_tag, color_confidence),
            (orientation_tag, orientation_confidence),
            (density_tag, density_confidence),
        ]
        tags = tuple(
            sorted(
                ((tag, round(conf, 4)) for tag, conf in candidates if tag not in existing),
                key=lambda pair: pair[1],
                reverse=True,
            )
        )
        return TagSuggestionResult(provider=self.name, model=MODEL_NAME, tags=tags)

    def moderate_image(self, *, image_bytes: bytes) -> ModerationResult:
        image = _decode(image_bytes)
        width, height = image.size
        stddev = _grayscale_stddev(image)

        categories: list[str] = []
        if width < _MIN_DIMENSION or height < _MIN_DIMENSION:
            categories.append("low_resolution")
        if stddev < _EXPECTED_STDDEV * 0.25:
            categories.append("low_variance")

        confidence = max(0.0, min(1.0, stddev / _EXPECTED_STDDEV))
        is_flagged = bool(categories)
        return ModerationResult(
            provider=self.name,
            model=MODEL_NAME,
            is_flagged=is_flagged,
            confidence=confidence,
            categories=tuple(categories),
        )

    def generate_design_image(
        self, *, prompt: str, allow_training: bool = False
    ) -> DesignImageResult:
        # `allow_training` has nothing to honor here — the local provider
        # never trains on anything — but it's still accepted (not just
        # dropped) so the interface stays identical to what a real provider
        # needs, per docs/ai-design-assistant.md#consent-for-provider-
        # training.
        image = _render_design_image(prompt)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return DesignImageResult(
            provider=self.name,
            model=MODEL_NAME,
            image_bytes=buffer.getvalue(),
            content_type="image/png",
            width=image.width,
            height=image.height,
            cost_usd=0.0,
        )


def cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Shared by similarity search and duplicate detection — both compare
    `DesignEmbedding` vectors the same way. Returns 0 for a degenerate
    (all-zero) vector rather than raising. Every vector here is
    non-negative (pixel/channel values normalized to 0..1 -- see
    `generate_embedding`), so the true result is always in [0, 1]; clamped
    to guard against floating-point drift pushing an identical-vector
    comparison a hair above 1.0, which would violate `DesignDuplicateMatch
    .similarity`'s `[0, 1]` CHECK constraint."""
    if len(a) != len(b):
        raise ValueError("Vectors must have the same dimension to compare.")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


__all__ = [
    "MODEL_NAME",
    "LocalHeuristicProvider",
    "cosine_similarity",
]

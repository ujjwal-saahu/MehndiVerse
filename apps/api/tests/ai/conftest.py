import io
from collections.abc import Generator

import httpx
import pytest
import respx
from PIL import Image
from sqlalchemy.orm import Session

from app.db.enums import DesignImageStatus
from app.db.models.design import Design, DesignImage
from app.services.ai.provider import (
    AiProvider,
    DesignImageResult,
    EmbeddingResult,
    ModerationResult,
    TagSuggestionResult,
)
from tests.auth.conftest import client  # noqa: F401  (re-exported fixture)
from tests.profile.conftest import storage_mock  # noqa: F401  (re-exported fixture)


def make_test_image_bytes(
    size: tuple[int, int] = (64, 64), color: tuple[int, int, int] = (200, 30, 30)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_ready_design_image(
    session: Session,
    *,
    design: Design,
    image_url: str = "https://example.test/designs/photo.png",
    is_primary: bool = True,
    sort_order: int = 0,
) -> DesignImage:
    image = DesignImage(
        design_id=design.id,
        image_url=image_url,
        status=DesignImageStatus.READY.value,
        is_primary=is_primary,
        sort_order=sort_order,
    )
    session.add(image)
    session.flush()
    return image


@pytest.fixture
def image_host_mock() -> Generator[respx.MockRouter, None, None]:
    """Mocks arbitrary `https://example.test/...` image URLs used by
    `app/services/ai/imaging.py::fetch_image_bytes` in tests — distinct from
    `storage_mock` (which is scoped to the Supabase Storage base URL) since
    AI capability tests fetch from a `DesignImage.image_url` directly."""
    with respx.mock(base_url="https://example.test") as router:
        yield router


class FakeProvider(AiProvider):
    """A configurable `AiProvider` test double — see docs/ai-design-
    assistant.md#keep-generation-provider-replaceable. Demonstrates that
    `app/services/ai/design_generation.py` only ever depends on the
    `AiProvider` interface: swapping in this fake (via monkeypatching
    `design_generation.get_ai_provider`, never a real network call)
    exercises the exact same code path a real cloud provider would run
    through."""

    name = "fake"

    def __init__(
        self,
        *,
        design_image_result: DesignImageResult | None = None,
        moderation_result: ModerationResult | None = None,
        raise_on_generate: Exception | None = None,
    ) -> None:
        self._design_image_result = design_image_result
        self._moderation_result = moderation_result
        self._raise_on_generate = raise_on_generate
        self.generate_design_image_calls: list[dict[str, object]] = []

    def suggest_tags(
        self, *, image_bytes: bytes, existing_tags: tuple[str, ...] = ()
    ) -> TagSuggestionResult:
        raise NotImplementedError("FakeProvider only implements the design-generation surface.")

    def generate_embedding(self, *, image_bytes: bytes) -> EmbeddingResult:
        raise NotImplementedError("FakeProvider only implements the design-generation surface.")

    def moderate_image(self, *, image_bytes: bytes) -> ModerationResult:
        if self._moderation_result is not None:
            return self._moderation_result
        return ModerationResult(
            provider=self.name, model="fake-v1", is_flagged=False, confidence=0.9
        )

    def generate_design_image(
        self, *, prompt: str, allow_training: bool = False
    ) -> DesignImageResult:
        self.generate_design_image_calls.append(
            {"prompt": prompt, "allow_training": allow_training}
        )
        if self._raise_on_generate is not None:
            raise self._raise_on_generate
        if self._design_image_result is not None:
            return self._design_image_result
        return DesignImageResult(
            provider=self.name,
            model="fake-v1",
            image_bytes=make_test_image_bytes(),
            content_type="image/png",
            width=64,
            height=64,
            cost_usd=0.02,
        )


def mock_design_upload(router: respx.MockRouter) -> None:
    router.post(url__regex=r"/object/ai-generated-designs/.*").mock(
        return_value=httpx.Response(200, json={"Key": "ai-generated-designs/mock"})
    )


def mock_design_sign(router: respx.MockRouter) -> None:
    router.post(url__regex=r"/object/sign/ai-generated-designs/.*").mock(
        return_value=httpx.Response(
            200, json={"signedURL": "/object/sign/ai-generated-designs/mock?token=abc"}
        )
    )


def mock_design_delete(router: respx.MockRouter) -> None:
    router.delete(url__regex=r"/object/ai-generated-designs/.*").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )


@pytest.fixture
def mock_ai_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    """Patches `app/services/ai/design_generation.py`'s bound reference to
    `get_ai_provider` (not `factory.get_ai_provider` itself — monkeypatching
    has to target where a name is *looked up*, not where it's defined) so
    `create_design_request`/`process_job` run against a `FakeProvider`
    instead of the real `LocalHeuristicProvider`, with no network access at
    all."""
    fake = FakeProvider()
    monkeypatch.setattr("app.services.ai.design_generation.get_ai_provider", lambda: fake)
    return fake

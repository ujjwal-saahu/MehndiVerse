from collections.abc import Generator

import pytest
import respx

from app.core.config import get_settings
from tests.profile.conftest import client  # noqa: F401  (re-exported fixture)


@pytest.fixture
def razorpay_mock() -> Generator[respx.MockRouter, None, None]:
    settings = get_settings()
    with respx.mock(base_url=settings.razorpay_api_base_url) as router:
        yield router

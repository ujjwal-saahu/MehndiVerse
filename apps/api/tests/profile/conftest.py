from collections.abc import Generator

import pytest
import respx

from app.core.config import get_settings
from tests.auth.conftest import client  # noqa: F401  (re-exported fixture)


@pytest.fixture
def storage_mock() -> Generator[respx.MockRouter, None, None]:
    settings = get_settings()
    with respx.mock(base_url=f"{settings.supabase_url}/storage/v1") as router:
        yield router

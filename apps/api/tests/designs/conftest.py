import httpx
import respx

from tests.profile.conftest import client, storage_mock  # noqa: F401


def mock_successful_storage_upload(storage_mock: respx.MockRouter) -> None:  # noqa: F811
    storage_mock.post(url__regex=r"/object/portfolio/.*").mock(
        return_value=httpx.Response(200, json={"Key": "portfolio/mock"})
    )

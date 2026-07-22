"""Selects which `AiProvider` implementation the app uses — see
docs/ai-foundation.md#provider-abstraction. Mirrors
`app/services/search/factory.py`/`app/services/payments/factory.py`
exactly: this is the *only* place that needs to change to add a real cloud
AI provider later.
"""

from app.core.config import get_settings

from .local_provider import LocalHeuristicProvider
from .provider import AiProvider


def get_ai_provider() -> AiProvider:
    provider_name = get_settings().ai_provider
    if provider_name == "local":
        return LocalHeuristicProvider()
    raise ValueError(f"Unknown AI provider: {provider_name!r}")

"""Selects which `SearchProvider` implementation the app uses — see
docs/design-search.md#search-provider-abstraction. This is the *only* place
that needs to change to add a Typesense/Meilisearch provider later.
"""

from app.core.config import get_settings

from .base import SearchProvider
from .postgres_provider import PostgresFullTextSearchProvider


def get_search_provider() -> SearchProvider:
    provider_name = get_settings().search_provider
    if provider_name == "postgres":
        return PostgresFullTextSearchProvider()
    raise ValueError(f"Unknown search provider: {provider_name!r}")

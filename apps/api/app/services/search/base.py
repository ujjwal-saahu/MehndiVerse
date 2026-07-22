"""Search-provider abstraction — see
docs/design-search.md#search-provider-abstraction.

Every concrete provider (Postgres full-text today; Typesense or Meilisearch
in a future phase) implements this same interface. `app/api/routes/search.py`
depends only on this module and `factory.py`'s `get_search_provider()` —
never on `postgres_provider.py` directly — so swapping the backing search
engine later never requires changing route code, only the factory's
provider selection (and adding the new provider module itself).
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.orm import Session

SearchSort = Literal["relevance", "newest", "popular", "most_saved"]
SuggestionType = Literal["design", "category", "artist"]


@dataclass(frozen=True)
class SearchFilters:
    category_ids: tuple[uuid.UUID, ...] = field(default_factory=tuple)
    artist_profile_id: uuid.UUID | None = None
    is_premium: bool | None = None
    difficulty_level: str | None = None
    body_placement: str | None = None


@dataclass(frozen=True)
class SearchPage:
    design_ids: list[uuid.UUID]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True)
class SuggestionHit:
    type: SuggestionType
    id: uuid.UUID
    label: str


class SearchProvider(ABC):
    """Returns ordered design ids, not hydrated `DesignSummaryOut`s — the
    route layer is responsible for turning ids back into summaries via
    `app/services/design_summaries.py`, so every provider implementation
    only ever needs to know about ids and ordering, not response shapes."""

    @abstractmethod
    def search(
        self,
        db: Session,
        *,
        query: str | None,
        filters: SearchFilters,
        sort: SearchSort,
        cursor: str | None,
        limit: int,
    ) -> SearchPage:
        raise NotImplementedError

    @abstractmethod
    def suggest(self, db: Session, *, query: str, limit: int) -> list[SuggestionHit]:
        raise NotImplementedError

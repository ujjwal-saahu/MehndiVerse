from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SearchSuggestionOut(BaseModel):
    type: str
    id: UUID
    label: str


class SearchHistoryItemOut(BaseModel):
    id: UUID
    query: str
    created_at: datetime

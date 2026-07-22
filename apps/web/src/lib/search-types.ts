/** Shapes returned by the backend's design-search endpoints (see
 * app/schemas/search.py, app/services/search/base.py) — shared across the
 * search page/components. */

export type SearchSuggestionType = "design" | "category" | "artist";

export interface SearchSuggestionData {
  type: SearchSuggestionType;
  id: string;
  label: string;
}

export interface SearchHistoryItemData {
  id: string;
  query: string;
  created_at: string;
}

export type SearchSort = "relevance" | "newest" | "popular" | "most_saved";

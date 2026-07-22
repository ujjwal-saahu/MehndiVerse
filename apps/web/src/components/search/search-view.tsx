"use client";

import { useCallback, useEffect, useState, type SubmitEvent } from "react";
import { useRouter } from "next/navigation";

import type { DesignCardData } from "@/components/design-grid/design-card";
import { DesignGrid } from "@/components/design-grid/design-grid";
import { fetchJson, sendRequest } from "@/lib/gallery-client";
import type { CategoryData, DesignListData, DesignSummaryData } from "@/lib/gallery-types";
import type { SearchHistoryItemData, SearchSort, SearchSuggestionData } from "@/lib/search-types";
import { useOnlineStatus } from "@/lib/use-online-status";

import { RecentSearches } from "./recent-searches";
import type { PremiumFilter } from "./search-filter-panel";
import { SearchFilterPanel } from "./search-filter-panel";
import { SearchSuggestionsDropdown } from "./search-suggestions-dropdown";

type SectionState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

interface ArtistFilter {
  id: string;
  label: string;
}

interface SearchState {
  query: string;
  categoryIds: string[];
  premium: PremiumFilter;
  sort: SearchSort;
  artist: ArtistFilter | null;
}

const INITIAL_STATE: SearchState = {
  query: "",
  categoryIds: [],
  premium: "any",
  sort: "relevance",
  artist: null,
};

const SUGGESTION_DEBOUNCE_MS = 300;
const MIN_SUGGESTION_LENGTH = 2;

function toCardData(design: DesignSummaryData): DesignCardData {
  return {
    id: design.id,
    title: design.title,
    imageUrl: design.thumbnail_url,
    artistName: design.artist_display_name ?? undefined,
    href: `/designs/${design.id}`,
  };
}

function hasActiveFilters(state: SearchState): boolean {
  return (
    state.categoryIds.length > 0 ||
    state.premium !== "any" ||
    state.sort !== "relevance" ||
    state.artist !== null
  );
}

/** Design search — see docs/design-search.md. Client-rendered end to end,
 * mirroring components/gallery/discover-view.tsx's structure (each section
 * owns its own loading/error/retry state). Filter/sort changes re-run the
 * search immediately; typing a keyword only re-runs on submit (Enter or the
 * search button), separately from the debounced suggestions fetch. */
export function SearchView() {
  const router = useRouter();
  const isOnline = useOnlineStatus();

  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [searchState, setSearchState] = useState<SearchState>(INITIAL_STATE);
  const [results, setResults] = useState<SectionState<DesignListData>>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchSuggestionData[]>([]);
  const [recentSearches, setRecentSearches] = useState<SearchHistoryItemData[]>([]);

  const offlineAwareMessage = useCallback(
    (error: Error) =>
      isOnline ? error.message : "You appear to be offline. Check your connection and try again.",
    [isOnline],
  );

  const loadRecentSearches = useCallback(() => {
    fetchJson<SearchHistoryItemData[]>("/api/designs/search/history")
      .then(setRecentSearches)
      .catch(() => {
        // Recent searches are a progressive enhancement — fail silently.
      });
  }, []);

  // Effect-safe: no synchronous setState before the fetch resolves (`results`
  // already starts as `{ status: "loading" }`) — mirrors
  // discover-view.tsx's fetchHomeFeed/loadHomeFeed split, required by the
  // react-hooks/set-state-in-effect rule.
  const fetchResults = useCallback(
    (next: SearchState, cursor?: string) => {
      const params = new URLSearchParams({ sort: next.sort, limit: "20" });
      const trimmedQuery = next.query.trim();
      if (trimmedQuery) params.set("q", trimmedQuery);
      next.categoryIds.forEach((id) => params.append("category_id", id));
      if (next.artist) params.set("artist_id", next.artist.id);
      if (next.premium !== "any") {
        params.set("is_premium", next.premium === "premium" ? "true" : "false");
      }
      if (cursor) params.set("cursor", cursor);

      fetchJson<DesignListData>(`/api/designs/search?${params.toString()}`)
        .then((data) => {
          setResults((current) => {
            if (cursor && current.status === "ready") {
              return {
                status: "ready",
                data: { items: [...current.data.items, ...data.items], page_info: data.page_info },
              };
            }
            return { status: "ready", data };
          });
          if (!cursor) loadRecentSearches();
        })
        .catch((error: Error) =>
          setResults({ status: "error", message: offlineAwareMessage(error) }),
        )
        .finally(() => setIsLoadingMore(false));
    },
    [offlineAwareMessage, loadRecentSearches],
  );

  // Event-handler-facing version: resets to "loading" first, safe here since
  // it's never called directly from an effect.
  const runSearch = useCallback(
    (next: SearchState, cursor?: string) => {
      if (cursor) {
        setIsLoadingMore(true);
      } else {
        setResults({ status: "loading" });
      }
      fetchResults(next, cursor);
    },
    [fetchResults],
  );

  useEffect(() => {
    fetchJson<CategoryData[]>("/api/categories")
      .then(setCategories)
      .catch(() => {
        // Filter panel categories are a progressive enhancement — fail silently.
      });
    loadRecentSearches();
    fetchResults(INITIAL_STATE);
    // Runs once on mount (plus again if connectivity flips, matching
    // DiscoverView's reconnect-refetch behavior via offlineAwareMessage).
  }, [fetchResults, loadRecentSearches]);

  // Only fetches (async, in the timeout callback) — never clears
  // `suggestions` synchronously in the effect body. The dropdown itself
  // hides stale suggestions once the query drops below the minimum length
  // (see the render below), so there's nothing to reset here.
  useEffect(() => {
    const trimmed = searchState.query.trim();
    if (trimmed.length < MIN_SUGGESTION_LENGTH) {
      return;
    }
    const timeout = setTimeout(() => {
      fetchJson<SearchSuggestionData[]>(
        `/api/designs/search/suggestions?q=${encodeURIComponent(trimmed)}`,
      )
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, SUGGESTION_DEBOUNCE_MS);
    return () => clearTimeout(timeout);
  }, [searchState.query]);

  const handleSubmit = (event: SubmitEvent) => {
    event.preventDefault();
    setSuggestions([]);
    runSearch(searchState);
  };

  const handleSelectSuggestion = (suggestion: SearchSuggestionData) => {
    setSuggestions([]);
    if (suggestion.type === "design") {
      router.push(`/designs/${suggestion.id}`);
      return;
    }
    if (suggestion.type === "artist") {
      const next: SearchState = {
        ...searchState,
        query: "",
        artist: { id: suggestion.id, label: suggestion.label },
      };
      setSearchState(next);
      runSearch(next);
      return;
    }
    if (!searchState.categoryIds.includes(suggestion.id)) {
      const next: SearchState = {
        ...searchState,
        query: "",
        categoryIds: [...searchState.categoryIds, suggestion.id],
      };
      setSearchState(next);
      runSearch(next);
    }
  };

  const handleToggleCategory = (id: string) => {
    const categoryIds = searchState.categoryIds.includes(id)
      ? searchState.categoryIds.filter((existing) => existing !== id)
      : [...searchState.categoryIds, id];
    const next: SearchState = { ...searchState, categoryIds };
    setSearchState(next);
    runSearch(next);
  };

  const handlePremiumChange = (premium: PremiumFilter) => {
    const next: SearchState = { ...searchState, premium };
    setSearchState(next);
    runSearch(next);
  };

  const handleSortChange = (sort: SearchSort) => {
    const next: SearchState = { ...searchState, sort };
    setSearchState(next);
    runSearch(next);
  };

  const handleClearArtistFilter = () => {
    const next: SearchState = { ...searchState, artist: null };
    setSearchState(next);
    runSearch(next);
  };

  const handleClearAllFilters = () => {
    const next: SearchState = { ...INITIAL_STATE, query: searchState.query };
    setSearchState(next);
    runSearch(next);
  };

  const handleSelectRecentSearch = (query: string) => {
    setSuggestions([]);
    const next: SearchState = { ...searchState, query };
    setSearchState(next);
    runSearch(next);
  };

  const handleClearHistory = () => {
    sendRequest("/api/designs/search/history", "DELETE")
      .then(() => setRecentSearches([]))
      .catch(() => {
        // Best-effort — the list simply won't clear if this fails.
      });
  };

  return (
    <div>
      <form onSubmit={handleSubmit} className="relative">
        <label htmlFor="search-query-input" className="sr-only">
          Search designs
        </label>
        <div className="flex gap-2">
          <input
            id="search-query-input"
            type="search"
            value={searchState.query}
            onChange={(event) =>
              setSearchState((current) => ({ ...current, query: event.target.value }))
            }
            onBlur={() => setTimeout(() => setSuggestions([]), 150)}
            placeholder="Search designs, styles, or artists…"
            className="flex-1 rounded-md border border-border bg-background px-4 py-2 text-text-primary"
          />
          <button
            type="submit"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
          >
            Search
          </button>
        </div>
        <SearchSuggestionsDropdown suggestions={suggestions} onSelect={handleSelectSuggestion} />
      </form>

      <RecentSearches
        items={recentSearches}
        onSelect={handleSelectRecentSearch}
        onClear={handleClearHistory}
      />

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[16rem_1fr]">
        <SearchFilterPanel
          categories={categories}
          selectedCategoryIds={searchState.categoryIds}
          onToggleCategory={handleToggleCategory}
          premium={searchState.premium}
          onPremiumChange={handlePremiumChange}
          sort={searchState.sort}
          onSortChange={handleSortChange}
          artistFilter={searchState.artist}
          onClearArtistFilter={handleClearArtistFilter}
          onClearAll={handleClearAllFilters}
          hasActiveFilters={hasActiveFilters(searchState)}
        />

        <div>
          <DesignGrid
            designs={results.status === "ready" ? results.data.items.map(toCardData) : []}
            isLoading={results.status === "loading"}
            error={results.status === "error" ? results.message : undefined}
            onRetry={() => runSearch(searchState)}
            emptyTitle="No designs found"
            emptyMessage="Try a different keyword or clear some filters."
            emptyAction={
              hasActiveFilters(searchState) ? (
                <button
                  type="button"
                  onClick={handleClearAllFilters}
                  className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
                >
                  Clear filters
                </button>
              ) : undefined
            }
          />
          {results.status === "ready" && results.data.page_info.has_more ? (
            <div className="mt-6 flex justify-center">
              <button
                type="button"
                disabled={isLoadingMore}
                onClick={() =>
                  runSearch(searchState, results.data.page_info.next_cursor ?? undefined)
                }
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoadingMore ? "Loading…" : "Load more"}
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

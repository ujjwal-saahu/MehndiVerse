"use client";

import type { SearchSuggestionData } from "@/lib/search-types";

interface SearchSuggestionsDropdownProps {
  suggestions: SearchSuggestionData[];
  onSelect: (suggestion: SearchSuggestionData) => void;
}

const TYPE_LABEL: Record<SearchSuggestionData["type"], string> = {
  design: "Design",
  category: "Category",
  artist: "Artist",
};

/** Type-ahead suggestions shown under the search input while typing — see
 * docs/design-search.md#search-suggestions. Selecting a "design" suggestion
 * navigates straight to it; "category"/"artist" apply as filters instead,
 * since those aren't a single result to jump to. */
export function SearchSuggestionsDropdown({
  suggestions,
  onSelect,
}: SearchSuggestionsDropdownProps) {
  if (suggestions.length === 0) return null;

  return (
    <ul
      role="listbox"
      aria-label="Search suggestions"
      className="absolute z-10 mt-1 w-full overflow-hidden rounded-md border border-border bg-surface shadow-lg"
    >
      {suggestions.map((suggestion) => (
        <li key={`${suggestion.type}-${suggestion.id}`}>
          <button
            type="button"
            role="option"
            aria-selected={false}
            onClick={() => onSelect(suggestion)}
            className="flex w-full items-center justify-between px-4 py-2 text-left text-sm text-text-primary hover:bg-surface-variant"
          >
            <span>{suggestion.label}</span>
            <span className="text-xs text-text-secondary">{TYPE_LABEL[suggestion.type]}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

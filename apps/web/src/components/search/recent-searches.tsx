"use client";

import type { SearchHistoryItemData } from "@/lib/search-types";

interface RecentSearchesProps {
  items: SearchHistoryItemData[];
  onSelect: (query: string) => void;
  onClear: () => void;
}

/** Per-user recent searches — see docs/design-search.md#search-history-and-recent-searches.
 * Renders nothing once cleared/empty rather than showing an empty panel. */
export function RecentSearches({ items, onSelect, onClear }: RecentSearchesProps) {
  if (items.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text-primary">Recent searches</span>
        <button
          type="button"
          onClick={onClear}
          className="text-sm font-medium text-primary hover:underline"
        >
          Clear
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item.query)}
            className="rounded-full bg-surface-variant px-3 py-1 text-sm text-text-primary hover:bg-border"
          >
            {item.query}
          </button>
        ))}
      </div>
    </div>
  );
}

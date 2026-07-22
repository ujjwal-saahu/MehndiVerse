"use client";

import type { CategoryData } from "@/lib/gallery-types";
import type { SearchSort } from "@/lib/search-types";

export type PremiumFilter = "any" | "free" | "premium";

interface ArtistFilter {
  id: string;
  label: string;
}

interface SearchFilterPanelProps {
  categories: CategoryData[];
  selectedCategoryIds: string[];
  onToggleCategory: (id: string) => void;
  premium: PremiumFilter;
  onPremiumChange: (value: PremiumFilter) => void;
  sort: SearchSort;
  onSortChange: (value: SearchSort) => void;
  artistFilter: ArtistFilter | null;
  onClearArtistFilter: () => void;
  onClearAll: () => void;
  hasActiveFilters: boolean;
}

const AXIS_ORDER = ["style", "occasion", "body_part", "difficulty", "density", "region"] as const;

const AXIS_LABELS: Record<(typeof AXIS_ORDER)[number], string> = {
  style: "Style",
  occasion: "Occasion",
  body_part: "Body Part",
  difficulty: "Difficulty",
  density: "Density",
  region: "Region",
};

const SORT_OPTIONS: { value: SearchSort; label: string }[] = [
  { value: "relevance", label: "Relevance" },
  { value: "newest", label: "Newest" },
  { value: "popular", label: "Most Viewed" },
  { value: "most_saved", label: "Most Saved" },
];

/** Multi-select category filters (one checkbox group per taxonomy axis — see
 * docs/design-search.md#category-filter-semantics: options within an axis
 * are OR'd, axes are AND'd together), plus premium/sort controls. */
export function SearchFilterPanel({
  categories,
  selectedCategoryIds,
  onToggleCategory,
  premium,
  onPremiumChange,
  sort,
  onSortChange,
  artistFilter,
  onClearArtistFilter,
  onClearAll,
  hasActiveFilters,
}: SearchFilterPanelProps) {
  const byAxis = AXIS_ORDER.map((axis) => ({
    axis,
    options: categories.filter((category) => category.category_type === axis),
  })).filter((group) => group.options.length > 0);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg font-semibold text-text-primary">Filters</h2>
        {hasActiveFilters ? (
          <button
            type="button"
            onClick={onClearAll}
            className="text-sm font-medium text-primary hover:underline"
          >
            Clear filters
          </button>
        ) : null}
      </div>

      {artistFilter ? (
        <div className="mt-4">
          <span className="mb-1 block text-sm font-medium text-text-primary">Artist</span>
          <span className="inline-flex items-center gap-2 rounded-full bg-surface-variant px-3 py-1 text-sm text-text-primary">
            {artistFilter.label}
            <button
              type="button"
              onClick={onClearArtistFilter}
              aria-label={`Remove artist filter: ${artistFilter.label}`}
              className="text-text-secondary hover:text-text-primary"
            >
              ×
            </button>
          </span>
        </div>
      ) : null}

      <div className="mt-4">
        <label
          htmlFor="search-sort-select"
          className="mb-1 block text-sm font-medium text-text-primary"
        >
          Sort by
        </label>
        <select
          id="search-sort-select"
          value={sort}
          onChange={(event) => onSortChange(event.target.value as SearchSort)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <fieldset className="mt-4">
        <legend className="mb-1 text-sm font-medium text-text-primary">Price</legend>
        <div className="flex gap-4">
          {(["any", "free", "premium"] as const).map((value) => (
            <label key={value} className="flex items-center gap-2 text-sm text-text-primary">
              <input
                type="radio"
                name="premium-filter"
                value={value}
                checked={premium === value}
                onChange={() => onPremiumChange(value)}
              />
              {value === "any" ? "Any" : value === "free" ? "Free" : "Premium"}
            </label>
          ))}
        </div>
      </fieldset>

      {byAxis.map(({ axis, options }) => (
        <fieldset key={axis} className="mt-4">
          <legend className="mb-1 text-sm font-medium text-text-primary">
            {AXIS_LABELS[axis]}
          </legend>
          <div className="flex flex-col gap-1.5">
            {options.map((category) => (
              <label
                key={category.id}
                className="flex items-center gap-2 text-sm text-text-primary"
              >
                <input
                  type="checkbox"
                  checked={selectedCategoryIds.includes(category.id)}
                  onChange={() => onToggleCategory(category.id)}
                />
                {category.name}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}

"use client";

import type { CategoryData } from "@/lib/gallery-types";

interface CategoryChipsProps {
  categories: CategoryData[];
  activeKey: string;
  onSelect: (key: string) => void;
}

const chipClass = (active: boolean) =>
  `rounded-full px-4 py-1.5 text-sm font-medium whitespace-nowrap ${
    active
      ? "bg-primary text-text-on-primary"
      : "bg-surface-variant text-text-primary hover:bg-border"
  }`;

/** "Home" shows the composite home feed (latest/featured/trending); "All
 * Designs" and each category switch to a paginated browse view — see
 * docs/design-gallery.md#category-browsing. */
export function CategoryChips({ categories, activeKey, onSelect }: CategoryChipsProps) {
  return (
    <div role="group" aria-label="Browse designs" className="flex gap-2 overflow-x-auto pb-1">
      <button
        type="button"
        aria-pressed={activeKey === "home"}
        onClick={() => onSelect("home")}
        className={chipClass(activeKey === "home")}
      >
        Home
      </button>
      <button
        type="button"
        aria-pressed={activeKey === "all"}
        onClick={() => onSelect("all")}
        className={chipClass(activeKey === "all")}
      >
        All Designs
      </button>
      {categories.map((category) => (
        <button
          key={category.id}
          type="button"
          aria-pressed={activeKey === category.id}
          onClick={() => onSelect(category.id)}
          className={chipClass(activeKey === category.id)}
        >
          {category.name}
        </button>
      ))}
    </div>
  );
}

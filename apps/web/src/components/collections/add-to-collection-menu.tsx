"use client";

import { useState } from "react";

import type { CollectionData, CollectionListData } from "@/lib/collection-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

/** "Add design to collection" — see docs/engagement-and-collections.md.
 * A lightweight dropdown of the user's own named collections (the default
 * "Saved Designs" collection is handled by the Save button, not this menu).
 * Clicking "Add" is idempotent — safe to click again even if the design is
 * already in that collection. */
export function AddToCollectionMenu({ designId }: { designId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [collections, setCollections] = useState<CollectionData[] | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const open = () => {
    setIsOpen((current) => !current);
    if (collections === null) {
      fetchJson<CollectionListData>("/api/collections?limit=50")
        .then((data) => setCollections(data.items.filter((collection) => !collection.is_default)))
        .catch((fetchError: Error) => setError(fetchError.message));
    }
  };

  const addTo = (collectionId: string) => {
    setError(null);
    mutateJson(`/api/collections/${collectionId}/items`, "POST", { design_id: designId })
      .then(() => setAddedIds((current) => new Set(current).add(collectionId)))
      .catch((addError: Error) => setError(addError.message));
  };

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={open}
        aria-expanded={isOpen}
        className="rounded-full border border-border bg-background px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
      >
        Add to collection
      </button>
      {isOpen ? (
        <div className="absolute z-10 mt-1 w-64 rounded-md border border-border bg-surface p-2 shadow-lg">
          {collections === null ? (
            <p className="px-2 py-1 text-sm text-text-secondary">Loading…</p>
          ) : collections.length === 0 ? (
            <p className="px-2 py-1 text-sm text-text-secondary">
              You don&apos;t have any collections yet.
            </p>
          ) : (
            <ul className="flex flex-col gap-1">
              {collections.map((collection) => (
                <li key={collection.id}>
                  <button
                    type="button"
                    onClick={() => addTo(collection.id)}
                    disabled={addedIds.has(collection.id)}
                    className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm text-text-primary hover:bg-surface-variant disabled:cursor-default disabled:opacity-70"
                  >
                    <span>{collection.name}</span>
                    {addedIds.has(collection.id) ? <span aria-hidden="true">✓</span> : null}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {error ? <p className="mt-1 px-2 text-sm text-danger">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

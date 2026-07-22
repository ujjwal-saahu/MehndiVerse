"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type SubmitEvent } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { CollectionData, CollectionItemsData } from "@/lib/collection-types";
import type { DesignSummaryData } from "@/lib/gallery-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

type MetaState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CollectionData };

type ItemsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CollectionItemsData };

// Fetched in one large page rather than the usual 20-per-page — reordering
// only makes sense against the collection's *entire* item list (the backend
// rejects a reorder that doesn't name every current item exactly once), and
// a personal collection is realistically well under this size. Very large
// collections still get a "Load more" button; reordering is just disabled
// until every item is loaded. See docs/engagement-and-collections.md.
const ITEMS_PAGE_SIZE = 100;

/** Collection detail — items grid, rename/delete, public/private toggle,
 * cover pick, remove item, and reorder (owner-only controls; everyone else
 * gets a read-only view when the collection is public). See
 * docs/engagement-and-collections.md. */
export function CollectionDetailView({ collectionId }: { collectionId: string }) {
  const router = useRouter();
  const [meta, setMeta] = useState<MetaState>({ status: "loading" });
  const [items, setItems] = useState<ItemsState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const loadMeta = useCallback(() => {
    fetchJson<CollectionData>(`/api/collections/${collectionId}`)
      .then((data) => {
        setMeta({ status: "ready", data });
        setNameDraft(data.name);
      })
      .catch((error: Error) => setMeta({ status: "error", message: error.message }));
  }, [collectionId]);

  const loadItems = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: String(ITEMS_PAGE_SIZE) });
      if (cursor) params.set("cursor", cursor);

      fetchJson<CollectionItemsData>(`/api/collections/${collectionId}/items?${params}`)
        .then((data) => {
          setItems((current) => {
            if (cursor && current.status === "ready") {
              return {
                status: "ready",
                data: { items: [...current.data.items, ...data.items], page_info: data.page_info },
              };
            }
            return { status: "ready", data };
          });
        })
        .catch((error: Error) => setItems({ status: "error", message: error.message }))
        .finally(() => setIsLoadingMore(false));
    },
    [collectionId],
  );

  useEffect(() => {
    loadMeta();
    loadItems();
  }, [loadMeta, loadItems]);

  const handleRename = (event: SubmitEvent) => {
    event.preventDefault();
    if (!nameDraft.trim()) return;
    setActionError(null);
    mutateJson<CollectionData>(`/api/collections/${collectionId}`, "PATCH", {
      name: nameDraft.trim(),
    })
      .then((data) => {
        setMeta({ status: "ready", data });
        setIsEditingName(false);
      })
      .catch((error: Error) => setActionError(error.message));
  };

  const handleTogglePrivacy = () => {
    if (meta.status !== "ready") return;
    setActionError(null);
    mutateJson<CollectionData>(`/api/collections/${collectionId}`, "PATCH", {
      is_private: !meta.data.is_private,
    })
      .then((data) => setMeta({ status: "ready", data }))
      .catch((error: Error) => setActionError(error.message));
  };

  const handleDelete = () => {
    if (!window.confirm("Delete this collection? This can't be undone.")) return;
    setActionError(null);
    mutateJson(`/api/collections/${collectionId}`, "DELETE")
      .then(() => router.push("/collections"))
      .catch((error: Error) => setActionError(error.message));
  };

  const handleRemoveItem = (designId: string) => {
    if (items.status !== "ready") return;
    const previous = items.data;
    setActionError(null);
    setItems({
      status: "ready",
      data: { ...previous, items: previous.items.filter((design) => design.id !== designId) },
    });
    mutateJson(`/api/collections/${collectionId}/items/${designId}`, "DELETE").catch(
      (error: Error) => {
        setItems({ status: "ready", data: previous });
        setActionError(error.message);
      },
    );
  };

  const handleMove = (index: number, direction: -1 | 1) => {
    if (items.status !== "ready") return;
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= items.data.items.length) return;

    const reordered = [...items.data.items];
    const moved = reordered[index];
    if (!moved) return;
    reordered.splice(index, 1);
    reordered.splice(nextIndex, 0, moved);
    const previous = items.data;
    setActionError(null);
    setItems({ status: "ready", data: { ...items.data, items: reordered } });

    mutateJson<CollectionItemsData>(`/api/collections/${collectionId}/items/reorder`, "PUT", {
      design_ids: reordered.map((design) => design.id),
    })
      .then((data) => setItems({ status: "ready", data }))
      .catch((error: Error) => {
        setItems({ status: "ready", data: previous });
        setActionError(error.message);
      });
  };

  const handleSetCover = (designId: string) => {
    setActionError(null);
    mutateJson<CollectionData>(`/api/collections/${collectionId}`, "PATCH", {
      cover_design_id: designId,
    })
      .then((data) => setMeta({ status: "ready", data }))
      .catch((error: Error) => setActionError(error.message));
  };

  if (meta.status === "loading") {
    return (
      <div aria-label="Loading collection" role="status">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="mt-4 h-4 w-1/2" />
      </div>
    );
  }

  if (meta.status === "error") {
    return <ErrorState message={meta.message} onRetry={loadMeta} />;
  }

  const collection = meta.data;
  const canReorder = items.status === "ready" && !items.data.page_info.has_more;

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {isEditingName ? (
            <form onSubmit={handleRename} className="flex items-center gap-2">
              <label htmlFor="collection-name-input" className="sr-only">
                Collection name
              </label>
              <input
                id="collection-name-input"
                type="text"
                value={nameDraft}
                onChange={(event) => setNameDraft(event.target.value)}
                className="rounded-md border border-border bg-background px-3 py-1.5 text-2xl font-semibold text-text-primary"
              />
              <button
                type="submit"
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsEditingName(false);
                  setNameDraft(collection.name);
                }}
                className="rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-variant"
              >
                Cancel
              </button>
            </form>
          ) : (
            <h1 className="font-display text-3xl font-semibold text-text-primary">
              {collection.name}
            </h1>
          )}
          <p className="mt-1 text-sm text-text-secondary">
            {collection.item_count} {collection.item_count === 1 ? "design" : "designs"} ·{" "}
            {collection.is_private ? "Private" : "Public"}
          </p>
          {collection.description ? (
            <p className="mt-2 text-text-primary">{collection.description}</p>
          ) : null}
        </div>

        {collection.is_owner && !collection.is_default ? (
          <div className="flex flex-wrap gap-2">
            {!isEditingName ? (
              <button
                type="button"
                onClick={() => setIsEditingName(true)}
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
              >
                Rename
              </button>
            ) : null}
            <button
              type="button"
              onClick={handleTogglePrivacy}
              className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              {collection.is_private ? "Make public" : "Make private"}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              className="rounded-md border border-danger px-3 py-1.5 text-sm font-medium text-danger hover:bg-danger-surface"
            >
              Delete
            </button>
          </div>
        ) : collection.is_owner ? (
          <button
            type="button"
            onClick={handleTogglePrivacy}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            {collection.is_private ? "Make public" : "Make private"}
          </button>
        ) : null}
      </div>

      {actionError ? <p className="mt-3 text-sm text-danger">{actionError}</p> : null}

      {collection.is_owner &&
      items.status === "ready" &&
      !canReorder &&
      items.data.items.length > 0 ? (
        <p className="mt-3 text-sm text-text-secondary">
          Load every design in this collection to reorder them.
        </p>
      ) : null}

      <div className="mt-8">
        {items.status === "error" ? (
          <ErrorState message={items.message} onRetry={() => loadItems()} />
        ) : items.status === "loading" ? (
          <div
            role="status"
            aria-label="Loading designs"
            className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
          >
            {Array.from({ length: 8 }).map((_, index) => (
              <Skeleton key={index} className="aspect-[3/4]" aria-label="Loading design" />
            ))}
          </div>
        ) : items.data.items.length === 0 ? (
          <EmptyState
            title="No designs yet"
            message="Add designs to this collection from any design's page using “Add to collection”."
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {items.data.items.map((design, index) => (
                <CollectionItemTile
                  key={design.id}
                  design={design}
                  isOwner={collection.is_owner}
                  canReorder={canReorder}
                  isFirst={index === 0}
                  isLast={index === items.data.items.length - 1}
                  isCover={
                    collection.cover_image_url !== null &&
                    design.thumbnail_url === collection.cover_image_url
                  }
                  onRemove={() => handleRemoveItem(design.id)}
                  onMoveUp={() => handleMove(index, -1)}
                  onMoveDown={() => handleMove(index, 1)}
                  onSetCover={() => handleSetCover(design.id)}
                />
              ))}
            </div>
            {items.data.page_info.has_more ? (
              <div className="mt-6 flex justify-center">
                <button
                  type="button"
                  disabled={isLoadingMore}
                  onClick={() => {
                    setIsLoadingMore(true);
                    loadItems(items.data.page_info.next_cursor ?? undefined);
                  }}
                  className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isLoadingMore ? "Loading…" : "Load more"}
                </button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

interface CollectionItemTileProps {
  design: DesignSummaryData;
  isOwner: boolean;
  canReorder: boolean;
  isFirst: boolean;
  isLast: boolean;
  isCover: boolean;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onSetCover: () => void;
}

function CollectionItemTile({
  design,
  isOwner,
  canReorder,
  isFirst,
  isLast,
  isCover,
  onRemove,
  onMoveUp,
  onMoveDown,
  onSetCover,
}: CollectionItemTileProps) {
  return (
    <div className="overflow-hidden rounded-xl bg-surface-variant shadow-sm">
      <Link href={`/designs/${design.id}`} className="relative block aspect-[3/4]">
        {design.thumbnail_url ? (
          <Image
            src={design.thumbnail_url}
            alt={`${design.title} mehndi design`}
            fill
            sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
            className="object-cover"
          />
        ) : null}
        {isCover ? (
          <span className="absolute left-2 top-2 rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-text-on-primary">
            Cover
          </span>
        ) : null}
      </Link>
      <div className="p-2">
        <p className="truncate text-sm font-medium text-text-primary">{design.title}</p>
        {isOwner ? (
          <div className="mt-2 flex flex-wrap gap-1">
            <button
              type="button"
              onClick={onSetCover}
              disabled={isCover}
              className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-background disabled:cursor-default disabled:opacity-50"
            >
              Set cover
            </button>
            <button
              type="button"
              onClick={onMoveUp}
              disabled={!canReorder || isFirst}
              className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-background disabled:cursor-not-allowed disabled:opacity-40"
            >
              ↑
            </button>
            <button
              type="button"
              onClick={onMoveDown}
              disabled={!canReorder || isLast}
              className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-background disabled:cursor-not-allowed disabled:opacity-40"
            >
              ↓
            </button>
            <button
              type="button"
              onClick={onRemove}
              className="rounded-md border border-danger px-2 py-1 text-xs text-danger hover:bg-danger-surface"
            >
              Remove
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

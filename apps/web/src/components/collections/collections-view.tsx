"use client";

import { useCallback, useEffect, useState, type SubmitEvent } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { CollectionData, CollectionListData } from "@/lib/collection-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";
import { useOnlineStatus } from "@/lib/use-online-status";

import { CollectionCard } from "./collection-card";

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CollectionListData };

/** The "My Collections" screen — list, create, and paginate through the
 * current user's own collections. See docs/engagement-and-collections.md. */
export function CollectionsView() {
  const isOnline = useOnlineStatus();
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const offlineAwareMessage = useCallback(
    (error: Error) =>
      isOnline ? error.message : "You appear to be offline. Check your connection and try again.",
    [isOnline],
  );

  const fetchCollections = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: "20" });
      if (cursor) params.set("cursor", cursor);

      fetchJson<CollectionListData>(`/api/collections?${params.toString()}`)
        .then((data) => {
          setState((current) => {
            if (cursor && current.status === "ready") {
              return {
                status: "ready",
                data: { items: [...current.data.items, ...data.items], page_info: data.page_info },
              };
            }
            return { status: "ready", data };
          });
        })
        .catch((error: Error) => setState({ status: "error", message: offlineAwareMessage(error) }))
        .finally(() => setIsLoadingMore(false));
    },
    [offlineAwareMessage],
  );

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const retry = () => {
    setState({ status: "loading" });
    fetchCollections();
  };

  const handleCreate = (event: SubmitEvent) => {
    event.preventDefault();
    if (!newName.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setCreateError(null);

    mutateJson<CollectionData>("/api/collections", "POST", { name: newName.trim() })
      .then((created) => {
        setState((current) =>
          current.status === "ready"
            ? {
                status: "ready",
                data: { ...current.data, items: [created, ...current.data.items] },
              }
            : current,
        );
        setNewName("");
        setIsCreating(false);
      })
      .catch((error: Error) => setCreateError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="sr-only">Your collections</h2>
        <button
          type="button"
          onClick={() => setIsCreating((current) => !current)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
        >
          New collection
        </button>
      </div>

      {isCreating ? (
        <form onSubmit={handleCreate} className="mt-4 flex flex-wrap items-start gap-2">
          <div>
            <label htmlFor="new-collection-name" className="sr-only">
              Collection name
            </label>
            <input
              id="new-collection-name"
              type="text"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder="Collection name"
              className="rounded-md border border-border bg-background px-4 py-2 text-text-primary"
            />
            {createError ? <p className="mt-1 text-sm text-danger">{createError}</p> : null}
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Creating…" : "Create"}
          </button>
        </form>
      ) : null}

      <div className="mt-6">
        {state.status === "error" ? (
          <ErrorState message={state.message} onRetry={retry} />
        ) : state.status === "loading" ? (
          <div
            role="status"
            aria-label="Loading collections"
            className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
          >
            {Array.from({ length: 8 }).map((_, index) => (
              <Skeleton key={index} className="aspect-[3/4]" aria-label="Loading collection" />
            ))}
          </div>
        ) : state.data.items.length === 0 ? (
          <EmptyState
            title="No collections yet"
            message="Create a collection to start organizing designs."
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {state.data.items.map((collection) => (
                <CollectionCard key={collection.id} collection={collection} />
              ))}
            </div>
            {state.data.page_info.has_more ? (
              <div className="mt-6 flex justify-center">
                <button
                  type="button"
                  disabled={isLoadingMore}
                  onClick={() => {
                    setIsLoadingMore(true);
                    fetchCollections(state.data.page_info.next_cursor ?? undefined);
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

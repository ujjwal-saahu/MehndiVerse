"use client";

import { useCallback, useEffect, useState } from "react";

import type { DesignCardData } from "@/components/design-grid/design-card";
import { DesignGrid } from "@/components/design-grid/design-grid";
import { fetchJson } from "@/lib/gallery-client";
import type { DesignListData, DesignSummaryData } from "@/lib/gallery-types";
import { useOnlineStatus } from "@/lib/use-online-status";

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DesignListData };

function toCardData(design: DesignSummaryData): DesignCardData {
  return {
    id: design.id,
    title: design.title,
    imageUrl: design.thumbnail_url,
    artistName: design.artist_display_name ?? undefined,
    href: `/designs/${design.id}`,
  };
}

/** The saved-designs screen — the quick-save shortcut's own view (designs
 * added via the heart/bookmark toggle on a design, i.e. the user's default
 * "Saved Designs" collection). See docs/engagement-and-collections.md. */
export function SavedDesignsView() {
  const isOnline = useOnlineStatus();
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const offlineAwareMessage = useCallback(
    (error: Error) =>
      isOnline ? error.message : "You appear to be offline. Check your connection and try again.",
    [isOnline],
  );

  const fetchSaved = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: "20" });
      if (cursor) params.set("cursor", cursor);

      fetchJson<DesignListData>(`/api/designs/saved?${params.toString()}`)
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

  const loadMore = (cursor: string) => {
    setIsLoadingMore(true);
    fetchSaved(cursor);
  };

  const retry = () => {
    setState({ status: "loading" });
    fetchSaved();
  };

  useEffect(() => {
    fetchSaved();
  }, [fetchSaved]);

  return (
    <div>
      <DesignGrid
        designs={state.status === "ready" ? state.data.items.map(toCardData) : []}
        isLoading={state.status === "loading"}
        error={state.status === "error" ? state.message : undefined}
        onRetry={retry}
        emptyTitle="No saved designs yet"
        emptyMessage="Tap the save icon on a design to add it here."
      />
      {state.status === "ready" && state.data.page_info.has_more ? (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            disabled={isLoadingMore}
            onClick={() => loadMore(state.data.page_info.next_cursor ?? "")}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

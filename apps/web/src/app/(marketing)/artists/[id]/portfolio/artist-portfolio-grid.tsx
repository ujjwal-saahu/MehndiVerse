"use client";

import { useCallback, useEffect, useState } from "react";

import { DesignGrid } from "@/components/design-grid/design-grid";
import type { DesignListData } from "@/lib/gallery-types";
import { fetchJson } from "@/lib/gallery-client";

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DesignListData };

export function ArtistPortfolioGrid({ artistId }: { artistId: string }) {
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchPage = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ artist_profile_id: artistId, limit: "24" });
      if (cursor) params.set("cursor", cursor);

      fetchJson<DesignListData>(`/api/designs?${params.toString()}`)
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
        .catch((error: Error) => setState({ status: "error", message: error.message }))
        .finally(() => setIsLoadingMore(false));
    },
    [artistId],
  );

  useEffect(() => {
    fetchPage();
  }, [fetchPage]);

  const designs =
    state.status === "ready"
      ? state.data.items.map((design) => ({
          id: design.id,
          title: design.title,
          imageUrl: design.thumbnail_url,
          href: `/designs/${design.id}`,
        }))
      : [];

  return (
    <>
      <DesignGrid
        designs={designs}
        isLoading={state.status === "loading"}
        error={state.status === "error" ? state.message : undefined}
        onRetry={() => fetchPage()}
        emptyTitle="No published designs yet"
      />
      {state.status === "ready" && state.data.page_info.has_more ? (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            disabled={isLoadingMore}
            onClick={() => {
              setIsLoadingMore(true);
              fetchPage(state.data.page_info.next_cursor ?? undefined);
            }}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      ) : null}
    </>
  );
}

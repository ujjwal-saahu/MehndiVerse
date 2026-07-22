"use client";

import { useCallback, useEffect, useState } from "react";

import type { DesignCardData } from "@/components/design-grid/design-card";
import { DesignGrid } from "@/components/design-grid/design-grid";
import { CategoryChips } from "@/components/gallery/category-chips";
import { DesignSection } from "@/components/gallery/design-section";
import { fetchJson } from "@/lib/gallery-client";
import type {
  CategoryData,
  DesignListData,
  DesignSummaryData,
  HomeFeedData,
} from "@/lib/gallery-types";
import { useOnlineStatus } from "@/lib/use-online-status";

type SectionState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

function toCardData(design: DesignSummaryData): DesignCardData {
  return {
    id: design.id,
    title: design.title,
    imageUrl: design.thumbnail_url,
    artistName: design.artist_display_name ?? undefined,
    href: `/designs/${design.id}`,
  };
}

/** Home feed (Latest/Featured/Trending) plus category-filtered, paginated
 * browsing — see docs/design-gallery.md#home-feed and #category-browsing.
 * Client-rendered end to end: every section needs its own retry action,
 * which requires client interactivity anyway. */
export function DiscoverView() {
  const isOnline = useOnlineStatus();
  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [activeKey, setActiveKey] = useState("home");
  const [homeFeed, setHomeFeed] = useState<SectionState<HomeFeedData>>({ status: "loading" });
  const [browse, setBrowse] = useState<SectionState<DesignListData>>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const offlineAwareMessage = useCallback(
    (error: Error) =>
      isOnline ? error.message : "You appear to be offline. Check your connection and try again.",
    [isOnline],
  );

  const loadCategories = useCallback(() => {
    fetchJson<CategoryData[]>("/api/categories")
      .then(setCategories)
      .catch(() => {
        // Category chips are a progressive enhancement over the home feed —
        // fail silently rather than blocking the whole page on them.
      });
  }, []);

  // No synchronous setState here — this is called directly from the mount
  // effect below, and `homeFeed` already starts as `{ status: "loading" }`,
  // so there's nothing to reset before the fetch resolves.
  const fetchHomeFeed = useCallback(() => {
    fetchJson<HomeFeedData>("/api/designs/home-feed")
      .then((data) => setHomeFeed({ status: "ready", data }))
      .catch((error: Error) =>
        setHomeFeed({ status: "error", message: offlineAwareMessage(error) }),
      );
  }, [offlineAwareMessage]);

  // The event-handler-facing version: resets to "loading" first (safe here
  // since it's never called from an effect) before re-fetching.
  const loadHomeFeed = useCallback(() => {
    setHomeFeed({ status: "loading" });
    fetchHomeFeed();
  }, [fetchHomeFeed]);

  const loadBrowse = useCallback(
    (categoryId: string | null, cursor?: string) => {
      const params = new URLSearchParams({ limit: "20" });
      if (categoryId) params.set("category_id", categoryId);
      if (cursor) params.set("cursor", cursor);

      if (cursor) {
        setIsLoadingMore(true);
      } else {
        setBrowse({ status: "loading" });
      }

      fetchJson<DesignListData>(`/api/designs?${params.toString()}`)
        .then((data) => {
          setBrowse((current) => {
            if (cursor && current.status === "ready") {
              return {
                status: "ready",
                data: { items: [...current.data.items, ...data.items], page_info: data.page_info },
              };
            }
            return { status: "ready", data };
          });
        })
        .catch((error: Error) =>
          setBrowse({ status: "error", message: offlineAwareMessage(error) }),
        )
        .finally(() => setIsLoadingMore(false));
    },
    [offlineAwareMessage],
  );

  useEffect(() => {
    loadCategories();
    fetchHomeFeed();
  }, [loadCategories, fetchHomeFeed]);

  const onSelectChip = (key: string) => {
    setActiveKey(key);
    if (key === "home") {
      loadHomeFeed();
      return;
    }
    loadBrowse(key === "all" ? null : key);
  };

  return (
    <div>
      <CategoryChips categories={categories} activeKey={activeKey} onSelect={onSelectChip} />

      {activeKey === "home" ? (
        <>
          <DesignSection
            title="Latest"
            designs={homeFeed.status === "ready" ? homeFeed.data.latest.map(toCardData) : []}
            isLoading={homeFeed.status === "loading"}
            error={homeFeed.status === "error" ? homeFeed.message : undefined}
            onRetry={loadHomeFeed}
            emptyMessage="New designs will show up here as artists publish them."
          />
          <DesignSection
            title="Featured"
            designs={homeFeed.status === "ready" ? homeFeed.data.featured.map(toCardData) : []}
            isLoading={homeFeed.status === "loading"}
            error={homeFeed.status === "error" ? homeFeed.message : undefined}
            onRetry={loadHomeFeed}
            emptyMessage="Featured picks will show up here soon."
          />
          <DesignSection
            title="Trending"
            designs={homeFeed.status === "ready" ? homeFeed.data.trending.map(toCardData) : []}
            isLoading={homeFeed.status === "loading"}
            error={homeFeed.status === "error" ? homeFeed.message : undefined}
            onRetry={loadHomeFeed}
            emptyMessage="Popular designs will show up here as people discover them."
          />
        </>
      ) : (
        <div className="mt-8">
          <DesignGrid
            designs={browse.status === "ready" ? browse.data.items.map(toCardData) : []}
            isLoading={browse.status === "loading"}
            error={browse.status === "error" ? browse.message : undefined}
            onRetry={() => loadBrowse(activeKey === "all" ? null : activeKey)}
            emptyTitle="No designs found"
            emptyMessage="Try a different category."
          />
          {browse.status === "ready" && browse.data.page_info.has_more ? (
            <div className="mt-6 flex justify-center">
              <button
                type="button"
                disabled={isLoadingMore}
                onClick={() =>
                  loadBrowse(
                    activeKey === "all" ? null : activeKey,
                    browse.data.page_info.next_cursor ?? undefined,
                  )
                }
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoadingMore ? "Loading…" : "Load more"}
              </button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AddToCollectionMenu } from "@/components/collections/add-to-collection-menu";
import type { DesignCardData } from "@/components/design-grid/design-card";
import { DesignGrid } from "@/components/design-grid/design-grid";
import { ErrorState } from "@/components/feedback/error-state";
import { ReportButton } from "@/components/feedback/report-button";
import { Skeleton } from "@/components/feedback/skeleton";
import { ArtistSummaryCard } from "@/components/gallery/artist-summary-card";
import { CommentsSection } from "@/components/gallery/comments-section";
import { ImageGallery } from "@/components/gallery/image-gallery";
import { LikeSaveButtons } from "@/components/gallery/like-save-buttons";
import { fetchJson } from "@/lib/gallery-client";
import type { DesignDetailData, DesignSummaryData } from "@/lib/gallery-types";
import { useOnlineStatus } from "@/lib/use-online-status";

type DetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DesignDetailData };

type RelatedState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: DesignSummaryData[] };

function toCardData(design: DesignSummaryData): DesignCardData {
  return {
    id: design.id,
    title: design.title,
    imageUrl: design.thumbnail_url,
    artistName: design.artist_display_name ?? undefined,
    href: `/designs/${design.id}`,
  };
}

/** The shareable design-detail view — see docs/design-gallery.md
 * #shareable-design-urls. Client-rendered so a failed load can offer a
 * retry action; the URL itself (`/designs/[id]`) is what makes it
 * shareable, independent of how the content is fetched.
 *
 * Keyed by `designId` at the call site below so navigating between two
 * designs (e.g. via a related-designs link) always starts this component's
 * state fresh — no stale previous-design content flashing while the new
 * fetch is in flight, and no need to synchronously reset state inside an
 * effect when `designId` changes underneath an already-mounted instance. */
export function DesignDetailView({ designId }: { designId: string }) {
  return <DesignDetailViewForId key={designId} designId={designId} />;
}

function DesignDetailViewForId({ designId }: { designId: string }) {
  const isOnline = useOnlineStatus();
  const [state, setState] = useState<DetailState>({ status: "loading" });
  const [related, setRelated] = useState<RelatedState>({ status: "loading" });
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const offlineAwareMessage = useCallback(
    (error: Error) =>
      isOnline ? error.message : "You appear to be offline. Check your connection and try again.",
    [isOnline],
  );

  // No synchronous setState here — called directly from the mount effect
  // below, and `state` already starts as `{ status: "loading" }`.
  const fetchDesign = useCallback(() => {
    fetchJson<DesignDetailData>(`/api/designs/${designId}`)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => setState({ status: "error", message: offlineAwareMessage(error) }));
  }, [designId, offlineAwareMessage]);

  // The retry-button-facing version: resets to "loading" first (safe here —
  // it's only ever called from a click handler, never from an effect).
  const load = useCallback(() => {
    setState({ status: "loading" });
    fetchDesign();
  }, [fetchDesign]);

  useEffect(() => {
    fetchDesign();
  }, [fetchDesign]);

  useEffect(() => {
    if (state.status !== "ready") return;
    // Fire-and-forget — a failed view-count ping shouldn't disrupt viewing
    // the design. See docs/design-gallery.md#view-count-event-handling.
    fetch(`/api/designs/${designId}/view`, { method: "POST" }).catch(() => {});
  }, [designId, state.status]);

  useEffect(() => {
    fetchJson<DesignSummaryData[]>(`/api/designs/${designId}/related`)
      .then((data) => setRelated({ status: "ready", data }))
      .catch(() => setRelated({ status: "error" }));
  }, [designId]);

  // Enforced on the backend (premium access + monthly quota) — see
  // docs/subscriptions-and-entitlements.md#download-limits. This button
  // never assumes it's allowed; a 403 here just surfaces the server's
  // reason (locked design, or quota used up this month).
  const downloadDesign = async () => {
    setDownloadError(null);
    setIsDownloading(true);
    try {
      const response = await fetch(`/api/designs/${designId}/download`, { method: "POST" });
      const body = (await response.json()) as { image_url?: string; message?: string };
      if (!response.ok) {
        setDownloadError(body.message ?? "Could not download this design.");
        return;
      }
      if (body.image_url) window.open(body.image_url, "_blank", "noopener,noreferrer");
    } catch {
      setDownloadError("Could not download this design.");
    } finally {
      setIsDownloading(false);
    }
  };

  if (state.status === "loading") {
    return (
      <div aria-label="Loading design" role="status">
        <Skeleton className="aspect-square w-full rounded-xl" />
        <Skeleton className="mt-4 h-8 w-2/3" />
        <Skeleton className="mt-2 h-4 w-1/3" />
      </div>
    );
  }

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }

  const design = state.data;

  return (
    <div>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <ImageGallery images={design.images} title={design.title} />

        <div>
          <h1 className="font-display text-3xl font-semibold text-text-primary">{design.title}</h1>
          <div className="mt-2 flex flex-wrap gap-x-2 text-sm text-text-secondary">
            {design.difficulty_level ? <span>{design.difficulty_level}</span> : null}
            {design.body_placement ? <span>· {design.body_placement}</span> : null}
            {design.is_premium ? <span>· Premium</span> : null}
          </div>

          {design.premium_locked ? (
            <p className="mt-3 rounded-md bg-surface-variant p-3 text-sm text-text-secondary">
              This is a premium design.{" "}
              <Link href="/pricing" className="text-primary hover:underline">
                Upgrade to a premium plan
              </Link>{" "}
              to see the full-resolution images.
            </p>
          ) : null}

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <LikeSaveButtons
              designId={design.id}
              initialIsLiked={design.is_liked}
              initialLikeCount={design.like_count}
              initialIsSaved={design.is_saved}
              initialSaveCount={design.save_count}
            />
            <AddToCollectionMenu designId={design.id} />
            {!design.premium_locked ? (
              <button
                type="button"
                onClick={() => void downloadDesign()}
                disabled={isDownloading}
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
              >
                {isDownloading ? "Preparing…" : "Download"}
              </button>
            ) : null}
            <ReportButton
              endpoint={`/api/designs/${design.id}/report`}
              label="Report design"
              promptMessage="Why are you reporting this design?"
              className="text-sm text-text-secondary hover:underline"
            />
          </div>
          {downloadError ? <p className="mt-2 text-sm text-danger">{downloadError}</p> : null}

          {design.description ? (
            <p className="mt-4 text-text-primary">{design.description}</p>
          ) : null}

          {design.categories.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {design.categories.map((category) => (
                <span
                  key={category.id}
                  className="rounded-full bg-surface-variant px-3 py-1 text-xs font-medium text-text-primary"
                >
                  {category.name}
                </span>
              ))}
            </div>
          ) : null}

          {design.artist ? (
            <div className="mt-6">
              <ArtistSummaryCard artist={design.artist} />
            </div>
          ) : null}
        </div>
      </div>

      <section className="mt-12">
        <h2 className="font-display text-xl font-semibold text-text-primary">Related designs</h2>
        <div className="mt-4">
          <DesignGrid
            designs={related.status === "ready" ? related.data.map(toCardData) : []}
            isLoading={related.status === "loading"}
            emptyTitle="No related designs yet"
            emptyMessage="Check back as more designs are added to this category."
            skeletonCount={4}
          />
        </div>
      </section>

      <CommentsSection designId={design.id} />
    </div>
  );
}

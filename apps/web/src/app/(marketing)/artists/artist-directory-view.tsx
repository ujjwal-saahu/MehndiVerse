"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { ArtistDirectoryListData } from "@/lib/artist-directory-types";
import { fetchJson } from "@/lib/gallery-client";

interface Filters {
  city: string;
  country: string;
  service: string;
  minRating: string;
  verifiedOnly: boolean;
}

const EMPTY_FILTERS: Filters = {
  city: "",
  country: "",
  service: "",
  minRating: "",
  verifiedOnly: true,
};

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ArtistDirectoryListData };

function buildQuery(filters: Filters, cursor?: string): string {
  const params = new URLSearchParams({ limit: "20" });
  if (filters.city.trim()) params.set("city", filters.city.trim());
  if (filters.country.trim()) params.set("country", filters.country.trim());
  if (filters.service.trim()) params.set("service", filters.service.trim());
  if (filters.minRating.trim()) params.set("min_rating", filters.minRating.trim());
  params.set("verified_only", String(filters.verifiedOnly));
  if (cursor) params.set("cursor", cursor);
  return params.toString();
}

/** Keyed by the submitted filter set in the parent so a new search remounts
 * with fresh "loading" state, rather than resetting state from inside an
 * effect (React's set-state-in-effect footgun) — same pattern as the admin
 * verification queue's QueueList. */
function ArtistList({ filters }: { filters: Filters }) {
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchPage = useCallback(
    (cursor?: string) => {
      fetchJson<ArtistDirectoryListData>(`/api/artists?${buildQuery(filters, cursor)}`)
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
    [filters],
  );

  useEffect(() => {
    fetchPage();
  }, [fetchPage]);

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={() => fetchPage()} />;
  }
  if (state.status === "loading") {
    return (
      <div
        role="status"
        aria-label="Loading artists"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-32" aria-label="Loading artist" />
        ))}
      </div>
    );
  }
  if (state.data.items.length === 0) {
    return <EmptyState title="No artists found" message="Try adjusting your filters." />;
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {state.data.items.map((artist) => (
          <Link
            key={artist.id}
            href={`/artists/${artist.id}`}
            className="flex items-start gap-3 rounded-xl border border-border bg-surface p-4 hover:bg-surface-variant"
          >
            <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full bg-surface-variant">
              {artist.avatar_url ? (
                <Image src={artist.avatar_url} alt="" fill sizes="56px" className="object-cover" />
              ) : null}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="truncate font-medium text-text-primary">{artist.display_name}</p>
                {artist.is_verified ? (
                  <span
                    title="Verified artist"
                    className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-info-surface text-[10px] text-info"
                  >
                    ✓
                  </span>
                ) : null}
              </div>
              {artist.headline ? (
                <p className="truncate text-sm text-text-secondary">{artist.headline}</p>
              ) : null}
              <p className="text-xs text-text-secondary">
                {[artist.city, artist.country].filter(Boolean).join(", ")}
              </p>
              <p className="mt-1 text-xs text-text-secondary">
                {artist.rating_count > 0
                  ? `★ ${artist.rating_average.toFixed(1)} (${artist.rating_count})`
                  : "No reviews yet"}
              </p>
            </div>
          </Link>
        ))}
      </div>
      {state.data.page_info.has_more ? (
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

export function ArtistDirectoryView() {
  const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);

  return (
    <div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setApplied(draft);
        }}
        className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4"
      >
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">City</span>
          <input
            type="text"
            value={draft.city}
            onChange={(event) => setDraft((current) => ({ ...current, city: event.target.value }))}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Country (e.g. IN)</span>
          <input
            type="text"
            value={draft.country}
            maxLength={2}
            onChange={(event) =>
              setDraft((current) => ({ ...current, country: event.target.value }))
            }
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Service</span>
          <input
            type="text"
            value={draft.service}
            placeholder="e.g. bridal henna"
            onChange={(event) =>
              setDraft((current) => ({ ...current, service: event.target.value }))
            }
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Min rating</span>
          <input
            type="number"
            min={0}
            max={5}
            step={0.5}
            value={draft.minRating}
            onChange={(event) =>
              setDraft((current) => ({ ...current, minRating: event.target.value }))
            }
            className="w-24 rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm text-text-primary">
          <input
            type="checkbox"
            checked={draft.verifiedOnly}
            onChange={(event) =>
              setDraft((current) => ({ ...current, verifiedOnly: event.target.checked }))
            }
          />
          Verified only
        </label>
        <button
          type="submit"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
        >
          Search
        </button>
      </form>

      <div className="mt-6">
        <ArtistList key={JSON.stringify(applied)} filters={applied} />
      </div>
    </div>
  );
}

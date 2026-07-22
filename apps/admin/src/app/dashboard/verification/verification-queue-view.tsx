"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import { fetchJson } from "@/lib/admin-client";
import type { ArtistVerificationQueueItemData } from "@/lib/admin-types";

interface QueuePage {
  items: ArtistVerificationQueueItemData[];
  page_info: { next_cursor: string | null; has_more: boolean };
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: QueuePage };

const FILTERS: { label: string; statuses: string[] }[] = [
  { label: "Needs review", statuses: ["submitted", "under_review"] },
  { label: "More info requested", statuses: ["more_information_required"] },
  { label: "Approved", statuses: ["approved"] },
  { label: "Rejected", statuses: ["rejected"] },
  { label: "Suspended", statuses: ["suspended"] },
  {
    label: "All artists",
    statuses: [
      "submitted",
      "under_review",
      "more_information_required",
      "approved",
      "rejected",
      "suspended",
    ],
  },
];

/** Also used by /dashboard/artists (Artist Management) via the
 * `defaultFilterIndex`/`showReactivate` props — see
 * docs/admin-dashboard.md#artist-management, which reuses this same
 * queue endpoint with every status visible rather than just the pending
 * review set. */
export function VerificationQueueView({ defaultFilterIndex = 0 }: { defaultFilterIndex?: number }) {
  const [filterIndex, setFilterIndex] = useState(defaultFilterIndex);
  const [search, setSearch] = useState("");

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((option, index) => (
            <button
              key={option.label}
              type="button"
              onClick={() => setFilterIndex(index)}
              className={`rounded-full px-3 py-1 text-sm font-medium ${
                index === filterIndex
                  ? "bg-primary text-text-on-primary"
                  : "bg-surface-variant text-text-secondary hover:bg-surface-variant/80"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by name…"
          aria-label="Search artists by name"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
      </div>

      <div className="mt-6">
        <QueueList
          key={`${filterIndex}-${search}`}
          statuses={FILTERS[filterIndex]!.statuses}
          search={search}
        />
      </div>
    </div>
  );
}

function QueueList({ statuses, search }: { statuses: string[]; search: string }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchQueue = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: "20" });
      for (const status of statuses) params.append("status_filter", status);
      if (search) params.set("search", search);
      if (cursor) params.set("cursor", cursor);

      fetchJson<QueuePage>(`/api/admin/artists?${params.toString()}`)
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
    [statuses, search],
  );

  useEffect(() => {
    fetchQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={() => fetchQueue()} />;
  }
  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading queue" className="flex flex-col gap-3">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-16" aria-label="Loading application" />
        ))}
      </div>
    );
  }
  if (state.data.items.length === 0) {
    return <EmptyState title="Nothing here" message="No applications match this filter." />;
  }

  return (
    <>
      <ul className="flex flex-col gap-3">
        {state.data.items.map((item) => (
          <li key={item.id}>
            <Link
              href={`/dashboard/verification/${item.id}`}
              className="flex items-center justify-between rounded-md border border-border bg-surface p-4 hover:bg-surface-variant"
            >
              <div>
                <p className="font-medium text-text-primary">
                  {item.professional_name ?? item.business_name ?? "Unnamed applicant"}
                </p>
                <p className="text-sm text-text-secondary">
                  {item.verification_status} · {item.document_count} document
                  {item.document_count === 1 ? "" : "s"}
                </p>
              </div>
              {item.submitted_at ? (
                <span className="text-xs text-text-secondary">
                  Submitted {new Date(item.submitted_at).toLocaleDateString()}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
      {state.data.page_info.has_more ? (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            disabled={isLoadingMore}
            onClick={() => {
              setIsLoadingMore(true);
              fetchQueue(state.data.page_info.next_cursor ?? undefined);
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

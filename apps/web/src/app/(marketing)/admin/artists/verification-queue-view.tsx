"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { ArtistVerificationQueueData, ArtistVerificationStatus } from "@/lib/artist-types";
import { VERIFICATION_STATUS_LABELS } from "@/lib/artist-types";
import { fetchJson } from "@/lib/gallery-client";

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ArtistVerificationQueueData };

const FILTER_OPTIONS: { label: string; statuses: ArtistVerificationStatus[] }[] = [
  { label: "Needs review", statuses: ["submitted", "under_review"] },
  { label: "More info requested", statuses: ["more_information_required"] },
  { label: "Approved", statuses: ["approved"] },
  { label: "Rejected", statuses: ["rejected"] },
  { label: "Suspended", statuses: ["suspended"] },
];

/** Keyed by filter index in the parent so switching filters remounts this
 * with fresh "loading" state, rather than resetting state from inside an
 * effect (React's set-state-in-effect footgun). */
function QueueList({ statuses }: { statuses: ArtistVerificationStatus[] }) {
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchQueue = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: "20" });
      for (const status of statuses) {
        params.append("status_filter", status);
      }
      if (cursor) params.set("cursor", cursor);

      fetchJson<ArtistVerificationQueueData>(`/api/admin/artists?${params.toString()}`)
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
    [statuses],
  );

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

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
              href={`/admin/artists/${item.id}`}
              className="flex items-center justify-between rounded-md border border-border bg-surface p-4 hover:bg-surface-variant"
            >
              <div>
                <p className="font-medium text-text-primary">
                  {item.professional_name ?? item.business_name ?? "Unnamed applicant"}
                </p>
                <p className="text-sm text-text-secondary">
                  {VERIFICATION_STATUS_LABELS[item.verification_status]} · {item.document_count}{" "}
                  document
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

export function VerificationQueueView() {
  const [filterIndex, setFilterIndex] = useState(0);

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {FILTER_OPTIONS.map((option, index) => (
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

      <div className="mt-6">
        <QueueList key={filterIndex} statuses={FILTER_OPTIONS[filterIndex]!.statuses} />
      </div>
    </div>
  );
}

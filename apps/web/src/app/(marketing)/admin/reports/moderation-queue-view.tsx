"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { ReportData, ReportQueueData, ReportQueueItemData } from "@/lib/community-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ReportQueueData };

const STATUS_FILTERS: { label: string; statuses: string[] }[] = [
  { label: "Pending", statuses: ["pending"] },
  { label: "Reviewing", statuses: ["reviewing"] },
  { label: "Resolved", statuses: ["resolved"] },
  { label: "Dismissed", statuses: ["dismissed"] },
];

function snapshotSummary(item: ReportQueueItemData): string {
  const snapshot = item.entity_snapshot;
  if (!snapshot) return "(no longer available)";
  if (typeof snapshot.title === "string") return snapshot.title;
  if (typeof snapshot.body === "string") return snapshot.body;
  if (typeof snapshot.display_name === "string") return snapshot.display_name ?? "(no name)";
  return JSON.stringify(snapshot);
}

function ReportRow({
  item,
  canAct,
  onResolved,
}: {
  item: ReportQueueItemData;
  canAct: boolean;
  onResolved: (updated: ReportQueueItemData) => void;
}) {
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const act = (action: "resolve" | "dismiss") => {
    const resolution_notes = window.prompt("Resolution notes (optional):") ?? null;
    setIsBusy(true);
    setError(null);
    mutateJson<ReportData>(`/api/admin/reports/${item.id}/${action}`, "POST", {
      resolution_notes,
    })
      .then((updated) => onResolved({ ...updated, entity_snapshot: item.entity_snapshot }))
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsBusy(false));
  };

  return (
    <li className="rounded-md border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-text-primary">
            {item.reported_entity_type} · {item.status}
          </p>
          <p className="mt-1 text-sm text-text-secondary">{item.reason}</p>
          <p className="mt-1 text-xs text-text-secondary">
            Reported content: {snapshotSummary(item)}
          </p>
        </div>
        {canAct && (item.status === "pending" || item.status === "reviewing") ? (
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              disabled={isBusy}
              onClick={() => act("resolve")}
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-text-on-primary disabled:opacity-60"
            >
              Resolve
            </button>
            <button
              type="button"
              disabled={isBusy}
              onClick={() => act("dismiss")}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-primary hover:bg-surface-variant disabled:opacity-60"
            >
              Dismiss
            </button>
          </div>
        ) : null}
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-xs text-danger">
          {error}
        </p>
      ) : null}
    </li>
  );
}

function QueueList({ statuses, canAct }: { statuses: string[]; canAct: boolean }) {
  const [state, setState] = useState<State>({ status: "loading" });

  const fetchQueue = useCallback(() => {
    const params = new URLSearchParams({ limit: "20" });
    for (const status of statuses) {
      params.append("status_filter", status);
    }
    fetchJson<ReportQueueData>(`/api/admin/reports?${params.toString()}`)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  }, [statuses]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={fetchQueue} />;
  }
  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading reports" className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-20" aria-label="Loading report" />
        ))}
      </div>
    );
  }
  if (state.data.items.length === 0) {
    return <EmptyState title="Nothing here" message="No reports match this filter." />;
  }

  return (
    <ul className="flex flex-col gap-3">
      {state.data.items.map((item) => (
        <ReportRow
          key={item.id}
          item={item}
          canAct={canAct}
          onResolved={(updated) =>
            setState((current) =>
              current.status === "ready"
                ? {
                    status: "ready",
                    data: {
                      ...current.data,
                      items: current.data.items.map((existing) =>
                        existing.id === updated.id ? updated : existing,
                      ),
                    },
                  }
                : current,
            )
          }
        />
      ))}
    </ul>
  );
}

export function ModerationQueueView({ canAct }: { canAct: boolean }) {
  const [filterIndex, setFilterIndex] = useState(0);

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((option, index) => (
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
        <QueueList
          key={filterIndex}
          statuses={STATUS_FILTERS[filterIndex]!.statuses}
          canAct={canAct}
        />
      </div>
    </div>
  );
}

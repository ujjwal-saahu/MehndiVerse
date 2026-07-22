"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { fetchJson, mutateJson } from "@/lib/admin-client";
import type { ReportQueueItemData } from "@/lib/admin-types";

interface QueuePage {
  items: ReportQueueItemData[];
  page_info: { next_cursor: string | null; has_more: boolean };
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: QueuePage };

const STATUS_FILTERS = ["pending", "reviewing", "resolved", "dismissed"];

function snapshotSummary(item: ReportQueueItemData): string {
  const snapshot = item.entity_snapshot;
  if (!snapshot) return "(no longer available)";
  if (typeof snapshot.title === "string") return snapshot.title;
  if (typeof snapshot.body === "string") return snapshot.body;
  if (typeof snapshot.display_name === "string") return snapshot.display_name;
  return JSON.stringify(snapshot);
}

export function ReportsQueueView({ canAct }: { canAct: boolean }) {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [state, setState] = useState<State>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [pendingAction, setPendingAction] = useState<{
    report: ReportQueueItemData;
    kind: "resolve" | "dismiss";
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchQueue = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: "20", status_filter: statusFilter });
      if (cursor) params.set("cursor", cursor);
      fetchJson<QueuePage>(`/api/admin/reports?${params.toString()}`)
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
    [statusFilter],
  );

  useEffect(() => {
    fetchQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const submitAction = (notes: string) => {
    if (!pendingAction) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/reports/${pendingAction.report.id}/${pendingAction.kind}`, "POST", {
      resolution_notes: notes,
    })
      .then(() => {
        setPendingAction(null);
        setState({ status: "loading" });
        fetchQueue();
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              s === statusFilter
                ? "bg-primary text-text-on-primary"
                : "bg-surface-variant text-text-secondary hover:bg-surface-variant/80"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {state.status === "error" ? (
          <ErrorState message={state.message} onRetry={() => fetchQueue()} />
        ) : state.status === "loading" ? (
          <div role="status" aria-label="Loading reports" className="flex flex-col gap-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-20" aria-label="Loading report" />
            ))}
          </div>
        ) : state.data.items.length === 0 ? (
          <EmptyState title="Nothing here" message="No reports match this filter." />
        ) : (
          <>
            <ul className="flex flex-col gap-3">
              {state.data.items.map((item) => (
                <li key={item.id} className="rounded-md border border-border bg-surface p-4">
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
                          onClick={() => setPendingAction({ report: item, kind: "resolve" })}
                          className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-text-on-primary"
                        >
                          Resolve
                        </button>
                        <button
                          type="button"
                          onClick={() => setPendingAction({ report: item, kind: "dismiss" })}
                          className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-primary hover:bg-surface-variant"
                        >
                          Dismiss
                        </button>
                      </div>
                    ) : null}
                  </div>
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
        )}
      </div>

      <ReasonDialog
        isOpen={pendingAction !== null}
        title={pendingAction?.kind === "resolve" ? "Resolve report" : "Dismiss report"}
        description="Resolution notes"
        confirmLabel={pendingAction?.kind === "resolve" ? "Resolve" : "Dismiss"}
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={submitAction}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  );
}

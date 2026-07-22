"use client";

import { useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { AdminBookingListItemData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

const ALL_STATUSES = [
  "draft",
  "requested",
  "artist_reviewing",
  "quotation_sent",
  "customer_reviewing",
  "confirmed",
  "deposit_pending",
  "deposit_paid",
  "in_progress",
  "completed",
  "cancelled",
  "refund_requested",
  "refunded",
  "disputed",
];

const DISPUTABLE_STATUSES = new Set([
  "confirmed",
  "deposit_pending",
  "deposit_paid",
  "in_progress",
]);
const RESOLUTION_TARGETS = ["completed", "cancelled", "refunded"];

type PendingAction =
  | { kind: "dispute"; booking: AdminBookingListItemData }
  | { kind: "resolve"; booking: AdminBookingListItemData; toStatus: string };

/** Shared by /dashboard/bookings (Booking Management, `mode="all"`) and
 * /dashboard/disputes (Dispute Management, `mode="disputes"`) — see
 * docs/admin-dashboard.md#dispute-management. Both views hit the same
 * `/admin/bookings` list endpoint; only the default status filter and the
 * available row actions differ. */
export function BookingsView({ canAct, mode }: { canAct: boolean; mode: "all" | "disputes" }) {
  const [status, setStatus] = useState(mode === "disputes" ? "disputed" : "");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const url = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
      sort_by: sortBy,
      sort_dir: sortDir,
    });
    if (status) params.set("status_filter", status);
    return `/api/admin/bookings?${params.toString()}`;
  }, [status, page, sortBy, sortDir]);

  const { state, reload } = useAdminList<AdminBookingListItemData>(url);

  const toggleSort = (key: string) => {
    if (sortBy === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("asc");
    }
  };

  const submitReason = (reason: string) => {
    if (!pendingAction) return;
    setIsSubmitting(true);
    setActionError(null);
    const request =
      pendingAction.kind === "dispute"
        ? mutateJson(`/api/admin/bookings/${pendingAction.booking.id}/dispute`, "POST", { reason })
        : mutateJson(`/api/admin/bookings/${pendingAction.booking.id}/resolve-dispute`, "POST", {
            to_status: pendingAction.toStatus,
            reason,
          });
    request
      .then(() => {
        setPendingAction(null);
        reload();
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<AdminBookingListItemData>[] = [
    {
      key: "customer",
      header: "Customer",
      render: (b) => b.customer_display_name ?? "—",
    },
    { key: "artist", header: "Artist", render: (b) => b.artist_display_name ?? "—" },
    { key: "status", header: "Status", sortKey: "status", render: (b) => b.status },
    {
      key: "requested_date",
      header: "Date",
      sortKey: "requested_date",
      render: (b) => (b.requested_date ? new Date(b.requested_date).toLocaleDateString() : "—"),
    },
    {
      key: "total_amount",
      header: "Total",
      sortKey: "total_amount",
      render: (b) => (b.total_amount !== null ? `${b.currency} ${b.total_amount}` : "—"),
    },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (b: AdminBookingListItemData) =>
              b.status === "disputed" ? (
                <div className="flex flex-wrap gap-2">
                  {RESOLUTION_TARGETS.map((target) => (
                    <button
                      key={target}
                      type="button"
                      onClick={() =>
                        setPendingAction({ kind: "resolve", booking: b, toStatus: target })
                      }
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      Resolve as {target}
                    </button>
                  ))}
                </div>
              ) : DISPUTABLE_STATUSES.has(b.status) ? (
                <button
                  type="button"
                  onClick={() => setPendingAction({ kind: "dispute", booking: b })}
                  className="text-xs font-medium text-danger hover:underline"
                >
                  Open dispute
                </button>
              ) : (
                <span className="text-xs text-text-secondary">—</span>
              ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        <select
          value={status}
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value);
          }}
          aria-label="Filter by status"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        >
          <option value="">All statuses</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {state.status === "error" ? (
        <div className="mt-6">
          <ErrorState message={state.message} onRetry={reload} />
        </div>
      ) : (
        <div className="mt-6">
          <DataTable
            columns={columns}
            rows={state.status === "ready" ? state.data.items : []}
            getRowKey={(b) => b.id}
            isLoading={state.status === "loading"}
            emptyTitle="No bookings found"
            emptyMessage="Try a different filter."
            sortBy={sortBy}
            sortDir={sortDir}
            onSortChange={toggleSort}
          />
          {state.status === "ready" ? (
            <Pagination
              page={state.data.page_info.page}
              totalPages={state.data.page_info.total_pages}
              total={state.data.page_info.total}
              onPageChange={setPage}
            />
          ) : null}
        </div>
      )}

      <ReasonDialog
        isOpen={pendingAction !== null}
        title={
          pendingAction?.kind === "dispute"
            ? "Open dispute"
            : `Resolve dispute as ${pendingAction?.toStatus ?? ""}`
        }
        confirmLabel={pendingAction?.kind === "dispute" ? "Open dispute" : "Resolve"}
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={submitReason}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  );
}

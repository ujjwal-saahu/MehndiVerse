"use client";

import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { AdminRefundListItemData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

const STATUS_OPTIONS = ["pending", "approved", "rejected", "processed"];

function formatAmount(amountMinor: number, currency: string): string {
  return `${currency} ${(amountMinor / 100).toFixed(2)}`;
}

export function RefundsView({ canAct }: { canAct: boolean }) {
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(1);
  const [pendingApprove, setPendingApprove] = useState<AdminRefundListItemData | null>(null);
  const [pendingReject, setPendingReject] = useState<AdminRefundListItemData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const url = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (status) params.set("status_filter", status);
    return `/api/admin/payments/refunds?${params.toString()}`;
  }, [status, page]);

  const { state, reload } = useAdminList<AdminRefundListItemData>(url);

  const approve = () => {
    if (!pendingApprove) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/payments/refunds/${pendingApprove.id}/approve`, "POST")
      .then(() => {
        setPendingApprove(null);
        reload();
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const reject = (reason: string) => {
    if (!pendingReject) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/payments/refunds/${pendingReject.id}/reject`, "POST", { reason })
      .then(() => {
        setPendingReject(null);
        reload();
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<AdminRefundListItemData>[] = [
    { key: "amount", header: "Amount", render: (r) => formatAmount(r.amount, r.currency) },
    { key: "reason", header: "Reason", render: (r) => r.reason ?? "—" },
    { key: "status", header: "Status", render: (r) => r.status },
    {
      key: "requested_at",
      header: "Requested",
      render: (r) => new Date(r.requested_at).toLocaleString(),
    },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (r: AdminRefundListItemData) =>
              r.status === "pending" ? (
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setPendingApprove(r)}
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => setPendingReject(r)}
                    className="text-sm font-medium text-danger hover:underline"
                  >
                    Reject
                  </button>
                </div>
              ) : (
                <span className="text-sm text-text-secondary">—</span>
              ),
          },
        ]
      : []),
  ];

  return (
    <div>
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
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {state.status === "error" ? (
        <div className="mt-6">
          <ErrorState message={state.message} onRetry={reload} />
        </div>
      ) : (
        <div className="mt-6">
          <DataTable
            columns={columns}
            rows={state.status === "ready" ? state.data.items : []}
            getRowKey={(r) => r.id}
            isLoading={state.status === "loading"}
            emptyTitle="No refunds found"
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

      <ConfirmDialog
        isOpen={pendingApprove !== null}
        title="Approve refund"
        message={
          pendingApprove
            ? `This will refund ${formatAmount(pendingApprove.amount, pendingApprove.currency)} to the customer via the payment provider. This cannot be undone.`
            : ""
        }
        confirmLabel="Approve refund"
        isDestructive
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={approve}
        onCancel={() => setPendingApprove(null)}
      />

      <ReasonDialog
        isOpen={pendingReject !== null}
        title="Reject refund"
        confirmLabel="Reject"
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={reject}
        onCancel={() => setPendingReject(null)}
      />
    </div>
  );
}

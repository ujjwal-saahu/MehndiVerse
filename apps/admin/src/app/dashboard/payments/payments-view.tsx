"use client";

import { useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import type { AdminPaymentListItemData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

const STATUS_OPTIONS = ["pending", "processing", "succeeded", "failed", "refunded"];

function formatAmount(amountMinor: number, currency: string): string {
  return `${currency} ${(amountMinor / 100).toFixed(2)}`;
}

/** Read-only platform-wide payment review — see docs/admin-dashboard.md
 * #payment-review. Refund/payout actions live in the separate Refunds
 * module (`/dashboard/refunds`), which is where money actually moves. */
export function PaymentsView() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const url = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
      sort_by: sortBy,
      sort_dir: sortDir,
    });
    if (status) params.set("status_filter", status);
    return `/api/admin/payments?${params.toString()}`;
  }, [status, page, sortBy, sortDir]);

  const { state, reload } = useAdminList<AdminPaymentListItemData>(url);

  const toggleSort = (key: string) => {
    if (sortBy === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("asc");
    }
  };

  const columns: DataTableColumn<AdminPaymentListItemData>[] = [
    {
      key: "amount",
      header: "Amount",
      sortKey: "amount",
      render: (p) => formatAmount(p.amount, p.currency),
    },
    { key: "type", header: "Type", render: (p) => p.payment_type },
    { key: "status", header: "Status", sortKey: "status", render: (p) => p.status },
    { key: "provider", header: "Provider", render: (p) => p.provider },
    {
      key: "created_at",
      header: "Date",
      sortKey: "created_at",
      render: (p) => new Date(p.created_at).toLocaleString(),
    },
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
            getRowKey={(p) => p.id}
            isLoading={state.status === "loading"}
            emptyTitle="No payments found"
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
    </div>
  );
}

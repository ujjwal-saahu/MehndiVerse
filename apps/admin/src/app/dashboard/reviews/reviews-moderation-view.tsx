"use client";

import { useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { AdminReviewListItemData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

interface PendingModeration {
  review: AdminReviewListItemData;
  action: "flag" | "unflag" | "remove" | "restore";
  title: string;
}

export function ReviewsModerationView({ canAct }: { canAct: boolean }) {
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [pending, setPending] = useState<PendingModeration | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const url = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (flaggedOnly) params.set("is_flagged", "true");
    return `/api/admin/reviews?${params.toString()}`;
  }, [flaggedOnly, page]);

  const { state, reload } = useAdminList<AdminReviewListItemData>(url);

  const submitModeration = (reason: string) => {
    if (!pending) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/reviews/${pending.review.id}/moderate`, "POST", {
      action: pending.action,
      reason,
    })
      .then(() => {
        setPending(null);
        reload();
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<AdminReviewListItemData>[] = [
    { key: "customer", header: "Customer", render: (r) => r.customer_display_name ?? "—" },
    { key: "rating", header: "Rating", render: (r) => "★".repeat(r.rating) },
    { key: "body", header: "Review", render: (r) => r.body ?? "—" },
    { key: "is_flagged", header: "Flagged", render: (r) => (r.is_flagged ? "Yes" : "No") },
    { key: "is_deleted", header: "Removed", render: (r) => (r.is_deleted ? "Yes" : "No") },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (r: AdminReviewListItemData) => (
              <div className="flex flex-wrap gap-2">
                {r.is_flagged ? (
                  <button
                    type="button"
                    onClick={() =>
                      setPending({ review: r, action: "unflag", title: "Unflag review" })
                    }
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Unflag
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setPending({ review: r, action: "flag", title: "Flag review" })}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Flag
                  </button>
                )}
                {r.is_deleted ? (
                  <button
                    type="button"
                    onClick={() =>
                      setPending({ review: r, action: "restore", title: "Restore review" })
                    }
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Restore
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() =>
                      setPending({ review: r, action: "remove", title: "Remove review" })
                    }
                    className="text-xs font-medium text-danger hover:underline"
                  >
                    Remove
                  </button>
                )}
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <label className="flex items-center gap-2 text-sm text-text-secondary">
        <input
          type="checkbox"
          checked={flaggedOnly}
          onChange={(event) => {
            setPage(1);
            setFlaggedOnly(event.target.checked);
          }}
        />
        Flagged only
      </label>

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
            emptyTitle="No reviews found"
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
        isOpen={pending !== null}
        title={pending?.title ?? ""}
        confirmLabel="Confirm"
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={submitModeration}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}

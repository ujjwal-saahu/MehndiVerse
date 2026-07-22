"use client";

import { useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { AdminDesignListItemData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

const STATUS_OPTIONS = ["draft", "published", "archived", "flagged"];

const MODERATE_ACTIONS: { action: string; label: string; title: string; targetStatus: string }[] = [
  { action: "publish", label: "Publish", title: "Publish design", targetStatus: "published" },
  { action: "unpublish", label: "Unpublish", title: "Unpublish design", targetStatus: "draft" },
  { action: "flag", label: "Flag", title: "Flag design for review", targetStatus: "flagged" },
  { action: "archive", label: "Archive", title: "Archive design", targetStatus: "archived" },
];

interface PendingModeration {
  design: AdminDesignListItemData;
  action: string;
  title: string;
}

export function DesignsView({ canAct }: { canAct: boolean }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [pending, setPending] = useState<PendingModeration | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const url = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
      sort_by: sortBy,
      sort_dir: sortDir,
    });
    if (search) params.set("search", search);
    if (status) params.set("status_filter", status);
    return `/api/admin/designs?${params.toString()}`;
  }, [search, status, page, sortBy, sortDir]);

  const { state, reload } = useAdminList<AdminDesignListItemData>(url);

  const toggleSort = (key: string) => {
    if (sortBy === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("asc");
    }
  };

  const submitModeration = (reason: string) => {
    if (!pending) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/designs/${pending.design.id}/moderate`, "POST", {
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

  const columns: DataTableColumn<AdminDesignListItemData>[] = [
    { key: "title", header: "Title", sortKey: "title", render: (d) => d.title },
    { key: "artist", header: "Artist", render: (d) => d.artist_display_name ?? "—" },
    { key: "status", header: "Status", sortKey: "status", render: (d) => d.status },
    { key: "view_count", header: "Views", sortKey: "view_count", render: (d) => d.view_count },
    { key: "like_count", header: "Likes", sortKey: "like_count", render: (d) => d.like_count },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (d: AdminDesignListItemData) => (
              <div className="flex flex-wrap gap-2">
                {MODERATE_ACTIONS.filter((a) => a.targetStatus !== d.status).map((a) => (
                  <button
                    key={a.action}
                    type="button"
                    onClick={() => setPending({ design: d, action: a.action, title: a.title })}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          value={search}
          onChange={(event) => {
            setPage(1);
            setSearch(event.target.value);
          }}
          placeholder="Search by title…"
          aria-label="Search designs by title"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
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
            getRowKey={(d) => d.id}
            isLoading={state.status === "loading"}
            emptyTitle="No designs found"
            emptyMessage="Try a different search or filter."
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
        isOpen={pending !== null}
        title={pending?.title ?? ""}
        description={pending ? `Design: ${pending.design.title}` : undefined}
        confirmLabel="Confirm"
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={submitModeration}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}

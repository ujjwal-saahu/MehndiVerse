"use client";

import { useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import type { GlobalAuditLogEntryData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

/** admin/super_admin only — see docs/admin-dashboard.md#audit-log-viewer.
 * Read-only: nothing here is ever edited or deleted, matching `AuditLog`'s
 * own "immutable, no updated_at, no soft delete, ever" design. */
export function AuditLogView() {
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);

  const url = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (entityType) params.set("entity_type", entityType);
    if (action) params.set("action", action);
    return `/api/admin/audit-logs?${params.toString()}`;
  }, [entityType, action, page]);

  const { state, reload } = useAdminList<GlobalAuditLogEntryData>(url);

  const columns: DataTableColumn<GlobalAuditLogEntryData>[] = [
    {
      key: "created_at",
      header: "When",
      render: (e) => new Date(e.created_at).toLocaleString(),
    },
    {
      key: "actor",
      header: "Actor",
      render: (e) => e.actor_display_name ?? e.actor_id ?? "System",
    },
    { key: "action", header: "Action", render: (e) => e.action },
    { key: "entity_type", header: "Entity", render: (e) => e.entity_type },
    {
      key: "details",
      header: "Details",
      render: (e) => (
        <span className="text-xs text-text-secondary">
          {e.after_state ? JSON.stringify(e.after_state) : "—"}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          value={entityType}
          onChange={(event) => {
            setPage(1);
            setEntityType(event.target.value);
          }}
          placeholder="Filter by entity type (e.g. users)"
          aria-label="Filter by entity type"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
        <input
          type="text"
          value={action}
          onChange={(event) => {
            setPage(1);
            setAction(event.target.value);
          }}
          placeholder="Filter by action (e.g. user.suspend)"
          aria-label="Filter by action"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
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
            getRowKey={(e) => e.id}
            isLoading={state.status === "loading"}
            emptyTitle="No audit log entries found"
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

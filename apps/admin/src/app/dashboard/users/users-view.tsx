"use client";

import { useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { AdminUserData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

const ROLE_OPTIONS = ["customer", "artist", "moderator", "administrator", "super_administrator"];
const STATUS_OPTIONS = ["active", "suspended", "deactivated", "pending_deletion"];

export function UsersView({ canAct }: { canAct: boolean }) {
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [pendingSuspend, setPendingSuspend] = useState<AdminUserData | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const url = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
      sort_by: sortBy,
      sort_dir: sortDir,
    });
    if (search) params.set("search", search);
    if (role) params.set("role", role);
    if (status) params.set("status_filter", status);
    return `/api/admin/users?${params.toString()}`;
  }, [search, role, status, page, sortBy, sortDir]);

  const { state, reload } = useAdminList<AdminUserData>(url);

  const toggleSort = (key: string) => {
    if (sortBy === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("asc");
    }
  };

  const suspend = (reason: string) => {
    if (!pendingSuspend) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/users/${pendingSuspend.id}/suspend`, "POST", { reason })
      .then(() => {
        setPendingSuspend(null);
        reload();
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const reactivate = (targetUser: AdminUserData) => {
    mutateJson(`/api/admin/users/${targetUser.id}/reactivate`, "POST").then(reload);
  };

  const columns: DataTableColumn<AdminUserData>[] = [
    { key: "email", header: "Email", sortKey: "email", render: (u) => u.email },
    { key: "display_name", header: "Name", render: (u) => u.display_name ?? "—" },
    { key: "role", header: "Role", sortKey: "role", render: (u) => u.role },
    { key: "status", header: "Status", sortKey: "status", render: (u) => u.status },
    {
      key: "created_at",
      header: "Joined",
      sortKey: "created_at",
      render: (u) => new Date(u.created_at).toLocaleDateString(),
    },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (u: AdminUserData) =>
              u.status === "suspended" ? (
                <button
                  type="button"
                  onClick={() => reactivate(u)}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  Reactivate
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setPendingSuspend(u)}
                  className="text-sm font-medium text-danger hover:underline"
                >
                  Suspend
                </button>
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
          placeholder="Search by email…"
          aria-label="Search users by email"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
        <select
          value={role}
          onChange={(event) => {
            setPage(1);
            setRole(event.target.value);
          }}
          aria-label="Filter by role"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        >
          <option value="">All roles</option>
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
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
            getRowKey={(u) => u.id}
            isLoading={state.status === "loading"}
            emptyTitle="No users found"
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
        isOpen={pendingSuspend !== null}
        title={`Suspend ${pendingSuspend?.email ?? ""}`}
        description="The user will be signed out and unable to use their account until reactivated."
        confirmLabel="Suspend"
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={suspend}
        onCancel={() => setPendingSuspend(null)}
      />
    </div>
  );
}

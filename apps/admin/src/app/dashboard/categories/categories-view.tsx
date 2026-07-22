"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { fetchJson, mutateJson } from "@/lib/admin-client";
import type { CategoryData } from "@/lib/admin-types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: CategoryData[] };

const CATEGORY_TYPES = ["style", "occasion", "body_part", "difficulty", "density", "region"];

/** Categories are a small, un-paginated taxonomy — the backend's `GET
 * /categories` returns a flat array, not a paged list, so this view
 * doesn't use `useAdminList`/`Pagination` the way every other module does.
 * See docs/admin-dashboard.md#category-management. */
export function CategoriesView({ canAct }: { canAct: boolean }) {
  const [search, setSearch] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<CategoryData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", slug: "", category_type: "style", sort_order: "0" });
  const [state, setState] = useState<State>({ status: "loading" });

  const url = useMemo(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (canAct && includeInactive) params.set("include_inactive", "true");
    const query = params.toString();
    return `/api/categories${query ? `?${query}` : ""}`;
  }, [search, includeInactive, canAct]);

  const fetchOnly = useCallback(() => {
    fetchJson<CategoryData[]>(url)
      .then((items) => setState({ status: "ready", items }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  }, [url]);

  useEffect(() => {
    fetchOnly();
  }, [fetchOnly]);

  const reload = useCallback(() => {
    setState({ status: "loading" });
    fetchOnly();
  }, [fetchOnly]);

  const createCategory = () => {
    setIsSubmitting(true);
    setFormError(null);
    mutateJson("/api/categories", "POST", {
      name: form.name,
      slug: form.slug,
      category_type: form.category_type,
      sort_order: Number(form.sort_order) || 0,
    })
      .then(() => {
        setForm({ name: "", slug: "", category_type: "style", sort_order: "0" });
        reload();
      })
      .catch((error: Error) => setFormError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const deleteCategory = () => {
    if (!pendingDelete) return;
    setIsSubmitting(true);
    mutateJson(`/api/categories/${pendingDelete.id}`, "DELETE")
      .then(() => {
        setPendingDelete(null);
        reload();
      })
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<CategoryData>[] = [
    { key: "name", header: "Name", render: (c) => c.name },
    { key: "type", header: "Type", render: (c) => c.category_type },
    { key: "sort_order", header: "Sort order", render: (c) => c.sort_order },
    { key: "is_active", header: "Active", render: (c) => (c.is_active ? "Yes" : "No") },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (c: CategoryData) =>
              c.is_active ? (
                <button
                  type="button"
                  onClick={() => setPendingDelete(c)}
                  className="text-sm font-medium text-danger hover:underline"
                >
                  Delete
                </button>
              ) : (
                <span className="text-sm text-text-secondary">Deleted</span>
              ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by name…"
          aria-label="Search categories by name"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
        {canAct ? (
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
            />
            Show deleted
          </label>
        ) : null}
      </div>

      {canAct ? (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
          <label className="flex flex-col text-sm text-text-secondary">
            Name
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <label className="flex flex-col text-sm text-text-secondary">
            Slug
            <input
              value={form.slug}
              onChange={(event) => setForm({ ...form, slug: event.target.value })}
              placeholder="bridal-mehndi"
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <label className="flex flex-col text-sm text-text-secondary">
            Type
            <select
              value={form.category_type}
              onChange={(event) => setForm({ ...form, category_type: event.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            >
              {CATEGORY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={isSubmitting || !form.name || !form.slug}
            onClick={createCategory}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
          >
            Add category
          </button>
          {formError ? (
            <p role="alert" className="text-sm text-danger">
              {formError}
            </p>
          ) : null}
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="mt-6">
          <ErrorState message={state.message} onRetry={reload} />
        </div>
      ) : (
        <div className="mt-6">
          <DataTable
            columns={columns}
            rows={state.status === "ready" ? state.items : []}
            getRowKey={(c) => c.id}
            isLoading={state.status === "loading"}
            emptyTitle="No categories found"
          />
        </div>
      )}

      <ConfirmDialog
        isOpen={pendingDelete !== null}
        title="Delete category"
        message={`"${pendingDelete?.name ?? ""}" will no longer be selectable for new designs.`}
        confirmLabel="Delete"
        isDestructive
        isSubmitting={isSubmitting}
        onConfirm={deleteCategory}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

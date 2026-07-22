"use client";

import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { TagData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

export function TagsView({ canAct }: { canAct: boolean }) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<TagData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", slug: "" });

  const url = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (search) params.set("search", search);
    return `/api/admin/tags?${params.toString()}`;
  }, [search, page]);

  const { state, reload } = useAdminList<TagData>(url);

  const createTag = () => {
    setIsSubmitting(true);
    setFormError(null);
    mutateJson("/api/admin/tags", "POST", form)
      .then(() => {
        setForm({ name: "", slug: "" });
        reload();
      })
      .catch((error: Error) => setFormError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const deleteTag = () => {
    if (!pendingDelete) return;
    setIsSubmitting(true);
    mutateJson(`/api/admin/tags/${pendingDelete.id}`, "DELETE")
      .then(() => {
        setPendingDelete(null);
        reload();
      })
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<TagData>[] = [
    { key: "name", header: "Name", render: (t) => t.name },
    { key: "slug", header: "Slug", render: (t) => t.slug },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (t: TagData) => (
              <button
                type="button"
                onClick={() => setPendingDelete(t)}
                className="text-sm font-medium text-danger hover:underline"
              >
                Delete
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <input
        type="search"
        value={search}
        onChange={(event) => {
          setPage(1);
          setSearch(event.target.value);
        }}
        placeholder="Search by name…"
        aria-label="Search tags by name"
        className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
      />

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
              placeholder="floral"
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <button
            type="button"
            disabled={isSubmitting || !form.name || !form.slug}
            onClick={createTag}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
          >
            Add tag
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
            rows={state.status === "ready" ? state.data.items : []}
            getRowKey={(t) => t.id}
            isLoading={state.status === "loading"}
            emptyTitle="No tags found"
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
        isOpen={pendingDelete !== null}
        title="Delete tag"
        message={`"${pendingDelete?.name ?? ""}" will be removed from every design that uses it.`}
        confirmLabel="Delete"
        isDestructive
        isSubmitting={isSubmitting}
        onConfirm={deleteTag}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { PromoBannerData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

export function BannersView({ canAct }: { canAct: boolean }) {
  const [page, setPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<PromoBannerData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", subtitle: "", image_url: "", link_url: "" });

  const url = useMemo(
    () => `/api/admin/banners?${new URLSearchParams({ page: String(page), page_size: "20" })}`,
    [page],
  );

  const { state, reload } = useAdminList<PromoBannerData>(url);

  const createBanner = () => {
    setIsSubmitting(true);
    setFormError(null);
    mutateJson("/api/admin/banners", "POST", {
      title: form.title,
      subtitle: form.subtitle || null,
      image_url: form.image_url,
      link_url: form.link_url || null,
    })
      .then(() => {
        setForm({ title: "", subtitle: "", image_url: "", link_url: "" });
        reload();
      })
      .catch((error: Error) => setFormError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const toggleActive = (banner: PromoBannerData) => {
    mutateJson(`/api/admin/banners/${banner.id}`, "PATCH", { is_active: !banner.is_active }).then(
      reload,
    );
  };

  const deleteBanner = () => {
    if (!pendingDelete) return;
    setIsSubmitting(true);
    mutateJson(`/api/admin/banners/${pendingDelete.id}`, "DELETE")
      .then(() => {
        setPendingDelete(null);
        reload();
      })
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<PromoBannerData>[] = [
    { key: "title", header: "Title", render: (b) => b.title },
    { key: "subtitle", header: "Subtitle", render: (b) => b.subtitle ?? "—" },
    { key: "is_active", header: "Active", render: (b) => (b.is_active ? "Yes" : "No") },
    { key: "sort_order", header: "Sort order", render: (b) => b.sort_order },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (b: PromoBannerData) => (
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => toggleActive(b)}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  {b.is_active ? "Deactivate" : "Activate"}
                </button>
                <button
                  type="button"
                  onClick={() => setPendingDelete(b)}
                  className="text-sm font-medium text-danger hover:underline"
                >
                  Delete
                </button>
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      {canAct ? (
        <div className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
          <label className="flex flex-col text-sm text-text-secondary">
            Title
            <input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <label className="flex flex-col text-sm text-text-secondary">
            Subtitle
            <input
              value={form.subtitle}
              onChange={(event) => setForm({ ...form, subtitle: event.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <label className="flex flex-col text-sm text-text-secondary">
            Image URL
            <input
              value={form.image_url}
              onChange={(event) => setForm({ ...form, image_url: event.target.value })}
              placeholder="https://…"
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <label className="flex flex-col text-sm text-text-secondary">
            Link URL
            <input
              value={form.link_url}
              onChange={(event) => setForm({ ...form, link_url: event.target.value })}
              placeholder="https://… (optional)"
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <button
            type="button"
            disabled={isSubmitting || !form.title || !form.image_url}
            onClick={createBanner}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
          >
            Add banner
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
            getRowKey={(b) => b.id}
            isLoading={state.status === "loading"}
            emptyTitle="No banners found"
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
        title="Delete banner"
        message={`"${pendingDelete?.title ?? ""}" will be permanently removed.`}
        confirmLabel="Delete"
        isDestructive
        isSubmitting={isSubmitting}
        onConfirm={deleteBanner}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

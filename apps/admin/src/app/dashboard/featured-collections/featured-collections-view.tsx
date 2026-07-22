"use client";

import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { FeaturedCollectionData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

export function FeaturedCollectionsView({ canAct }: { canAct: boolean }) {
  const [page, setPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<FeaturedCollectionData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", description: "" });
  const [designIdByCollection, setDesignIdByCollection] = useState<Record<string, string>>({});
  const [itemError, setItemError] = useState<Record<string, string>>({});

  const url = useMemo(
    () =>
      `/api/admin/featured-collections?${new URLSearchParams({ page: String(page), page_size: "10" })}`,
    [page],
  );

  const { state, reload } = useAdminList<FeaturedCollectionData>(url);

  const createCollection = () => {
    setIsSubmitting(true);
    setFormError(null);
    mutateJson("/api/admin/featured-collections", "POST", {
      title: form.title,
      description: form.description || null,
    })
      .then(() => {
        setForm({ title: "", description: "" });
        reload();
      })
      .catch((error: Error) => setFormError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const deleteCollection = () => {
    if (!pendingDelete) return;
    setIsSubmitting(true);
    mutateJson(`/api/admin/featured-collections/${pendingDelete.id}`, "DELETE")
      .then(() => {
        setPendingDelete(null);
        reload();
      })
      .finally(() => setIsSubmitting(false));
  };

  const toggleActive = (collection: FeaturedCollectionData) => {
    mutateJson(`/api/admin/featured-collections/${collection.id}`, "PATCH", {
      is_active: !collection.is_active,
    }).then(reload);
  };

  const addItem = (collection: FeaturedCollectionData) => {
    const designId = designIdByCollection[collection.id]?.trim();
    if (!designId) return;
    setItemError((current) => ({ ...current, [collection.id]: "" }));
    mutateJson(`/api/admin/featured-collections/${collection.id}/items`, "POST", {
      design_id: designId,
    })
      .then(() => {
        setDesignIdByCollection((current) => ({ ...current, [collection.id]: "" }));
        reload();
      })
      .catch((error: Error) =>
        setItemError((current) => ({ ...current, [collection.id]: error.message })),
      );
  };

  const removeItem = (collection: FeaturedCollectionData, itemId: string) => {
    mutateJson(`/api/admin/featured-collections/${collection.id}/items/${itemId}`, "DELETE").then(
      reload,
    );
  };

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={reload} />;
  }

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
            Description
            <input
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <button
            type="button"
            disabled={isSubmitting || !form.title}
            onClick={createCollection}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
          >
            Add collection
          </button>
          {formError ? (
            <p role="alert" className="text-sm text-danger">
              {formError}
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-4">
        {state.status === "loading" ? (
          <p className="text-sm text-text-secondary">Loading…</p>
        ) : state.data.items.length === 0 ? (
          <p className="text-sm text-text-secondary">No featured collections yet.</p>
        ) : (
          state.data.items.map((collection) => (
            <div key={collection.id} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-text-primary">{collection.title}</p>
                  {collection.description ? (
                    <p className="text-sm text-text-secondary">{collection.description}</p>
                  ) : null}
                  <p className="text-xs text-text-secondary">
                    {collection.is_active ? "Active" : "Inactive"} · {collection.items.length}{" "}
                    design
                    {collection.items.length === 1 ? "" : "s"}
                  </p>
                </div>
                {canAct ? (
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => toggleActive(collection)}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      {collection.is_active ? "Deactivate" : "Activate"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setPendingDelete(collection)}
                      className="text-sm font-medium text-danger hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                ) : null}
              </div>

              {collection.items.length > 0 ? (
                <ul className="mt-3 flex flex-wrap gap-2">
                  {collection.items.map((item) => (
                    <li
                      key={item.id}
                      className="flex items-center gap-2 rounded-full bg-surface-variant px-3 py-1 text-xs text-text-primary"
                    >
                      {item.design_id.slice(0, 8)}…
                      {canAct ? (
                        <button
                          type="button"
                          onClick={() => removeItem(collection, item.id)}
                          aria-label={`Remove design ${item.design_id}`}
                          className="text-danger hover:underline"
                        >
                          ×
                        </button>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}

              {canAct ? (
                <div className="mt-3 flex items-center gap-2">
                  <input
                    value={designIdByCollection[collection.id] ?? ""}
                    onChange={(event) =>
                      setDesignIdByCollection((current) => ({
                        ...current,
                        [collection.id]: event.target.value,
                      }))
                    }
                    placeholder="Design ID"
                    aria-label={`Add design to ${collection.title}`}
                    className="rounded-md border border-border bg-background px-3 py-1.5 text-sm text-text-primary"
                  />
                  <button
                    type="button"
                    onClick={() => addItem(collection)}
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    Add design
                  </button>
                  {itemError[collection.id] ? (
                    <span role="alert" className="text-xs text-danger">
                      {itemError[collection.id]}
                    </span>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))
        )}
      </div>

      {state.status === "ready" ? (
        <Pagination
          page={state.data.page_info.page}
          totalPages={state.data.page_info.total_pages}
          total={state.data.page_info.total}
          onPageChange={setPage}
        />
      ) : null}

      <ConfirmDialog
        isOpen={pendingDelete !== null}
        title="Delete featured collection"
        message={`"${pendingDelete?.title ?? ""}" will be permanently removed.`}
        confirmLabel="Delete"
        isDestructive
        isSubmitting={isSubmitting}
        onConfirm={deleteCollection}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

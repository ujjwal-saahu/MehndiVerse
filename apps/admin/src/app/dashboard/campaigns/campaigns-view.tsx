"use client";

import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { Pagination } from "@/components/table/pagination";
import { mutateJson } from "@/lib/admin-client";
import type { NotificationCampaignData } from "@/lib/admin-types";
import { useAdminList } from "@/lib/use-admin-list";

const TARGET_ROLES = [
  "",
  "customer",
  "artist",
  "moderator",
  "administrator",
  "super_administrator",
];

export function CampaignsView({ canAct }: { canAct: boolean }) {
  const [page, setPage] = useState(1);
  const [pendingSend, setPendingSend] = useState<NotificationCampaignData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", body: "", target_role: "" });

  const url = useMemo(
    () =>
      `/api/admin/notification-campaigns?${new URLSearchParams({ page: String(page), page_size: "20" })}`,
    [page],
  );

  const { state, reload } = useAdminList<NotificationCampaignData>(url);

  const createCampaign = () => {
    setIsSubmitting(true);
    setFormError(null);
    mutateJson("/api/admin/notification-campaigns", "POST", {
      title: form.title,
      body: form.body,
      target_role: form.target_role || null,
    })
      .then(() => {
        setForm({ title: "", body: "", target_role: "" });
        reload();
      })
      .catch((error: Error) => setFormError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const sendCampaign = () => {
    if (!pendingSend) return;
    setIsSubmitting(true);
    setSendError(null);
    mutateJson(`/api/admin/notification-campaigns/${pendingSend.id}/send`, "POST")
      .then(() => {
        setPendingSend(null);
        reload();
      })
      .catch((error: Error) => setSendError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<NotificationCampaignData>[] = [
    { key: "title", header: "Title", render: (c) => c.title },
    { key: "target_role", header: "Target", render: (c) => c.target_role ?? "Everyone" },
    { key: "status", header: "Status", render: (c) => c.status },
    { key: "recipient_count", header: "Recipients", render: (c) => c.recipient_count ?? "—" },
    ...(canAct
      ? [
          {
            key: "actions",
            header: "Actions",
            render: (c: NotificationCampaignData) =>
              c.status === "draft" ? (
                <button
                  type="button"
                  onClick={() => setPendingSend(c)}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  Send
                </button>
              ) : (
                <span className="text-sm text-text-secondary">
                  Sent {c.sent_at ? new Date(c.sent_at).toLocaleString() : ""}
                </span>
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
            Target
            <select
              value={form.target_role}
              onChange={(event) => setForm({ ...form, target_role: event.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            >
              {TARGET_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r || "Everyone"}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-64 flex-1 flex-col text-sm text-text-secondary">
            Message
            <textarea
              value={form.body}
              onChange={(event) => setForm({ ...form, body: event.target.value })}
              rows={2}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
            />
          </label>
          <button
            type="button"
            disabled={isSubmitting || !form.title || !form.body}
            onClick={createCampaign}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
          >
            Save draft
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
            getRowKey={(c) => c.id}
            isLoading={state.status === "loading"}
            emptyTitle="No campaigns yet"
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
        isOpen={pendingSend !== null}
        title="Send campaign"
        message={
          pendingSend
            ? `This will immediately notify every ${pendingSend.target_role ?? "user"} — this cannot be undone.`
            : ""
        }
        confirmLabel="Send now"
        isDestructive
        isSubmitting={isSubmitting}
        error={sendError}
        onConfirm={sendCampaign}
        onCancel={() => setPendingSend(null)}
      />
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { DataTable, type DataTableColumn } from "@/components/table/data-table";
import { fetchJson, mutateJson } from "@/lib/admin-client";
import type { SystemSettingData } from "@/lib/admin-types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: SystemSettingData[] };

/** super_admin only — see docs/admin-dashboard.md#super-admin-only-modules.
 * `value` is arbitrary JSON (`SystemSetting.value` is a JSONB column), so
 * the form takes it as raw JSON text rather than trying to build a
 * generic form for every possible shape. */
export function SettingsView() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [key, setKey] = useState("");
  const [valueText, setValueText] = useState("{}");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchOnly = () => {
    fetchJson<{ items: SystemSettingData[] }>("/api/admin/settings")
      .then((data) => setState({ status: "ready", items: data.items }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  };

  useEffect(() => {
    fetchOnly();
  }, []);

  const reload = () => {
    setState({ status: "loading" });
    fetchOnly();
  };

  const upsert = () => {
    setFormError(null);
    let value: unknown;
    try {
      value = JSON.parse(valueText);
    } catch {
      setFormError("Value must be valid JSON.");
      return;
    }
    setIsSubmitting(true);
    mutateJson(`/api/admin/settings/${key}`, "PUT", {
      value,
      description: description || null,
      is_public: isPublic,
    })
      .then(() => {
        setKey("");
        setValueText("{}");
        setDescription("");
        setIsPublic(false);
        reload();
      })
      .catch((error: Error) => setFormError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  const columns: DataTableColumn<SystemSettingData>[] = [
    { key: "key", header: "Key", render: (s) => s.key },
    { key: "value", header: "Value", render: (s) => JSON.stringify(s.value) },
    { key: "is_public", header: "Public", render: (s) => (s.is_public ? "Yes" : "No") },
    {
      key: "updated_at",
      header: "Updated",
      render: (s) => new Date(s.updated_at).toLocaleString(),
    },
  ];

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
        <label className="flex flex-col text-sm text-text-secondary">
          Key
          <input
            value={key}
            onChange={(event) => setKey(event.target.value)}
            placeholder="maintenance_mode"
            className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
          />
        </label>
        <label className="flex flex-col text-sm text-text-secondary">
          Description
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
          />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={isPublic}
            onChange={(event) => setIsPublic(event.target.checked)}
          />
          Public
        </label>
        <label className="flex min-w-64 flex-1 flex-col text-sm text-text-secondary">
          Value (JSON)
          <textarea
            value={valueText}
            onChange={(event) => setValueText(event.target.value)}
            rows={2}
            className="mt-1 rounded-md border border-border px-3 py-2 font-mono text-sm text-text-primary"
          />
        </label>
        <button
          type="button"
          disabled={isSubmitting || !key}
          onClick={upsert}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
        >
          Save setting
        </button>
        {formError ? (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        ) : null}
      </div>

      {state.status === "error" ? (
        <div className="mt-6">
          <ErrorState message={state.message} onRetry={reload} />
        </div>
      ) : (
        <div className="mt-6">
          <DataTable
            columns={columns}
            rows={state.status === "ready" ? state.items : []}
            getRowKey={(s) => s.id}
            isLoading={state.status === "loading"}
            emptyTitle="No settings configured yet"
          />
        </div>
      )}
    </div>
  );
}

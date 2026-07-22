"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { SubmitButton } from "@/components/forms/submit-button";
import type { BlockedDateData, BlockType } from "@/lib/scheduling-types";
import { BLOCK_TYPE_LABELS } from "@/lib/scheduling-types";
import { fetchJson, mutateJson, sendRequest } from "@/lib/gallery-client";

export function BlocksSection() {
  const [blocks, setBlocks] = useState<BlockedDateData[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [blockType, setBlockType] = useState<BlockType>("vacation");
  const [isTimeScoped, setIsTimeScoped] = useState(false);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [reason, setReason] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = () => {
    fetchJson<BlockedDateData[]>("/api/artist/availability/blocks")
      .then(setBlocks)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(load, []);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!startDate) {
      setFormError("Start date is required.");
      return;
    }
    setIsCreating(true);
    setFormError(null);
    try {
      const created = await mutateJson<BlockedDateData>("/api/artist/availability/blocks", "POST", {
        start_date: startDate,
        end_date: isTimeScoped ? startDate : endDate || startDate,
        block_type: blockType,
        start_time: isTimeScoped ? `${startTime}:00` : null,
        end_time: isTimeScoped ? `${endTime}:00` : null,
        reason: reason.trim() || null,
      });
      setBlocks((current) => (current ? [...current, created] : [created]));
      setReason("");
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setIsCreating(false);
    }
  };

  const remove = async (block: BlockedDateData) => {
    try {
      await sendRequest(`/api/artist/availability/blocks/${block.id}`, "DELETE");
      setBlocks((current) => current?.filter((b) => b.id !== block.id) ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4"
      >
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">Type</span>
            <select
              value={blockType}
              onChange={(event) => setBlockType(event.target.value as BlockType)}
              className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
            >
              {(Object.keys(BLOCK_TYPE_LABELS) as BlockType[]).map((type) => (
                <option key={type} value={type}>
                  {BLOCK_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">Start date</span>
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
            />
          </label>
          {!isTimeScoped ? (
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-text-secondary">End date</span>
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
              />
            </label>
          ) : null}
        </div>

        <label className="flex items-center gap-2 text-sm text-text-primary">
          <input
            type="checkbox"
            checked={isTimeScoped}
            onChange={(event) => setIsTimeScoped(event.target.checked)}
          />
          Only block specific hours on this day (manual schedule block)
        </label>

        {isTimeScoped ? (
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-text-secondary">From</span>
              <input
                type="time"
                value={startTime}
                onChange={(event) => setStartTime(event.target.value)}
                className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-text-secondary">To</span>
              <input
                type="time"
                value={endTime}
                onChange={(event) => setEndTime(event.target.value)}
                className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
              />
            </label>
          </div>
        ) : null}

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Reason (optional)</span>
          <input
            type="text"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>

        {formError ? <p className="text-sm text-danger">{formError}</p> : null}
        <SubmitButton isSubmitting={isCreating} loadingLabel="Adding…">
          Add block
        </SubmitButton>
      </form>

      {blocks === null ? (
        <p className="text-sm text-text-secondary">Loading…</p>
      ) : blocks.length === 0 ? (
        <EmptyState title="No blocked dates" message="Add a holiday, leave, or time off above." />
      ) : (
        <div className="flex flex-col gap-2">
          {blocks.map((block) => (
            <div
              key={block.id}
              className="flex items-center justify-between rounded-md border border-border bg-surface p-3"
            >
              <div className="text-sm text-text-primary">
                <span className="font-medium">{BLOCK_TYPE_LABELS[block.block_type]}</span>{" "}
                {block.start_date === block.end_date
                  ? block.start_date
                  : `${block.start_date} – ${block.end_date}`}
                {block.start_time
                  ? ` · ${block.start_time.slice(0, 5)}–${block.end_time?.slice(0, 5)}`
                  : ""}
                {block.reason ? ` — ${block.reason}` : ""}
              </div>
              <button
                type="button"
                onClick={() => void remove(block)}
                className="rounded-md border border-border px-3 py-1 text-sm font-medium text-text-primary hover:bg-surface-variant"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

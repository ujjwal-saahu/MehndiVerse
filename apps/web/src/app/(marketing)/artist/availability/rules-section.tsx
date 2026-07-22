"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { SubmitButton } from "@/components/forms/submit-button";
import type { AvailabilityRuleData } from "@/lib/scheduling-types";
import { DAY_NAMES } from "@/lib/scheduling-types";
import { fetchJson, mutateJson, sendRequest } from "@/lib/gallery-client";

function formatTime(value: string): string {
  return value.slice(0, 5);
}

export function RulesSection() {
  const [rules, setRules] = useState<AvailabilityRuleData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dayOfWeek, setDayOfWeek] = useState("1");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [isCreating, setIsCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = () => {
    fetchJson<AvailabilityRuleData[]>("/api/artist/availability/rules")
      .then(setRules)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(load, []);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsCreating(true);
    setFormError(null);
    try {
      const created = await mutateJson<AvailabilityRuleData>(
        "/api/artist/availability/rules",
        "POST",
        {
          day_of_week: Number(dayOfWeek),
          start_time: `${startTime}:00`,
          end_time: `${endTime}:00`,
        },
      );
      setRules((current) => (current ? [...current, created] : [created]));
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setIsCreating(false);
    }
  };

  const toggleActive = async (rule: AvailabilityRuleData) => {
    try {
      const updated = await mutateJson<AvailabilityRuleData>(
        `/api/artist/availability/rules/${rule.id}`,
        "PATCH",
        { is_active: !rule.is_active },
      );
      setRules((current) => current?.map((r) => (r.id === updated.id ? updated : r)) ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const remove = async (rule: AvailabilityRuleData) => {
    try {
      await sendRequest(`/api/artist/availability/rules/${rule.id}`, "DELETE");
      setRules((current) => current?.filter((r) => r.id !== rule.id) ?? null);
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
        className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4"
      >
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Day</span>
          <select
            value={dayOfWeek}
            onChange={(event) => setDayOfWeek(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          >
            {DAY_NAMES.map((name, index) => (
              <option key={name} value={index}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Start</span>
          <input
            type="time"
            value={startTime}
            onChange={(event) => setStartTime(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">End</span>
          <input
            type="time"
            value={endTime}
            onChange={(event) => setEndTime(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <SubmitButton isSubmitting={isCreating} loadingLabel="Adding…">
          Add hours
        </SubmitButton>
        {formError ? <p className="w-full text-sm text-danger">{formError}</p> : null}
      </form>

      {rules === null ? (
        <p className="text-sm text-text-secondary">Loading…</p>
      ) : rules.length === 0 ? (
        <EmptyState title="No weekly hours set" message="Add your working hours above." />
      ) : (
        <div className="flex flex-col gap-2">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center justify-between rounded-md border border-border bg-surface p-3"
            >
              <span className="text-sm text-text-primary">
                {DAY_NAMES[rule.day_of_week]} {formatTime(rule.start_time)}–
                {formatTime(rule.end_time)}
                {!rule.is_active ? " (inactive)" : ""}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void toggleActive(rule)}
                  className="rounded-md border border-border px-3 py-1 text-sm font-medium text-text-primary hover:bg-surface-variant"
                >
                  {rule.is_active ? "Deactivate" : "Activate"}
                </button>
                <button
                  type="button"
                  onClick={() => void remove(rule)}
                  className="rounded-md border border-border px-3 py-1 text-sm font-medium text-text-primary hover:bg-surface-variant"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

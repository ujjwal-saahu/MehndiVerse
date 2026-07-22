"use client";

import { useState } from "react";

import type { CalendarViewData } from "@/lib/scheduling-types";
import { DAY_NAMES } from "@/lib/scheduling-types";
import { fetchJson } from "@/lib/gallery-client";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDaysIso(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function CalendarSection() {
  const [startDate, setStartDate] = useState(todayIso());
  const [view, setView] = useState<CalendarViewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const load = async (start: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchJson<CalendarViewData>(
        `/api/artist/availability/calendar?start_date=${start}&end_date=${addDaysIso(start, 13)}`,
      );
      setView(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Starting from</span>
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          />
        </label>
        <button
          type="button"
          disabled={isLoading}
          onClick={() => void load(startDate)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Loading…" : "Show two weeks"}
        </button>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      {view ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {view.days.map((day) => (
            <div
              key={day.date}
              className={`rounded-md border p-3 text-sm ${
                day.is_available ? "border-border bg-surface" : "border-border bg-surface-variant"
              }`}
            >
              <p className="font-medium text-text-primary">
                {DAY_NAMES[day.day_of_week]} {day.date}
              </p>
              {day.windows.length > 0 ? (
                <p className="text-text-secondary">
                  {day.windows
                    .map((w) => `${w.start_time.slice(0, 5)}–${w.end_time.slice(0, 5)}`)
                    .join(", ")}
                </p>
              ) : (
                <p className="text-text-secondary">No hours set</p>
              )}
              {day.blocks.length > 0 ? (
                <p className="text-danger">
                  {day.blocks.length} block{day.blocks.length === 1 ? "" : "s"}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

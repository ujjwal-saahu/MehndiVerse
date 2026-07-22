"use client";

import { useState } from "react";

import type { ArtistServiceData } from "@/lib/artist-directory-types";
import type { AvailableSlotsData } from "@/lib/scheduling-types";
import { fetchJson } from "@/lib/gallery-client";

function addDaysIso(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Read-only slot browsing — see
 * docs/artist-scheduling.md#available-slot-calculation. Deliberately does
 * not create a booking; that's a later phase. Slot times are shown in the
 * viewer's own browser timezone (via `toLocaleString`), converted client-side
 * from the UTC instants the API returns. */
export function CheckAvailabilityWidget({
  artistId,
  services,
}: {
  artistId: string;
  services: ArtistServiceData[];
}) {
  const bookableServices = services.filter((s) => s.duration_minutes !== null);
  const [serviceId, setServiceId] = useState(bookableServices[0]?.id ?? "");
  const [startDate, setStartDate] = useState(todayIso());
  const [slots, setSlots] = useState<AvailableSlotsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (bookableServices.length === 0) {
    return null;
  }

  const checkAvailability = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        service_id: serviceId,
        start_date: startDate,
        end_date: addDaysIso(startDate, 6),
      });
      const data = await fetchJson<AvailableSlotsData>(
        `/api/artists/${artistId}/availability/slots?${params.toString()}`,
      );
      setSlots(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="mt-8">
      <h2 className="font-display text-lg font-semibold text-text-primary">Check availability</h2>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Service</span>
          <select
            value={serviceId}
            onChange={(event) => setServiceId(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-text-primary"
          >
            {bookableServices.map((service) => (
              <option key={service.id} value={service.id}>
                {service.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Week starting</span>
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
          onClick={() => void checkAvailability()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Checking…" : "Check availability"}
        </button>
      </div>

      {error ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      ) : null}

      {slots ? (
        slots.slots.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">No open slots in this week.</p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {slots.slots.map((slot) => (
              <span
                key={slot.start}
                className="rounded-full border border-border px-3 py-1 text-sm text-text-primary"
              >
                {new Date(slot.start).toLocaleString(undefined, {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </span>
            ))}
          </div>
        )
      ) : null}
      <p className="mt-2 text-xs text-text-secondary">
        Times shown in your local timezone. Use &quot;Request a booking&quot; above to start a
        request — this preview doesn&apos;t book a specific slot.
      </p>
    </section>
  );
}

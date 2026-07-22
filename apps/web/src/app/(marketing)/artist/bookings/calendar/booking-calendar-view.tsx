"use client";

import Link from "next/link";
import { useState } from "react";

import { BOOKING_STATUS_LABELS } from "@/lib/booking-types";
import type { BookingSummaryData } from "@/lib/booking-types";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDaysIso(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function BookingCalendarView() {
  const [startDate, setStartDate] = useState(todayIso());
  const [bookings, setBookings] = useState<BookingSummaryData[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (rangeDays: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const endDate = addDaysIso(startDate, rangeDays - 1);
      const response = await fetch(
        `/api/artist/bookings/calendar?start_date=${startDate}&end_date=${endDate}`,
      );
      const body = (await response.json()) as BookingSummaryData[] | { message: string };
      if (!response.ok) {
        setError((body as { message: string }).message);
        return;
      }
      setBookings(body as BookingSummaryData[]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-sm text-text-secondary">
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
          />
        </label>
        <button
          type="button"
          onClick={() => load(7)}
          disabled={isLoading}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          Show one week
        </button>
        <button
          type="button"
          onClick={() => load(14)}
          disabled={isLoading}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          Show two weeks
        </button>
      </div>

      {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}

      {bookings !== null ? (
        bookings.length === 0 ? (
          <p className="mt-6 text-sm text-text-secondary">No occupying bookings in this range.</p>
        ) : (
          <ul className="mt-6 flex flex-col gap-3">
            {bookings.map((booking) => (
              <li key={booking.id}>
                <Link
                  href={`/bookings/${booking.id}`}
                  className="flex items-center justify-between rounded-xl border border-border bg-surface p-4 hover:bg-surface-variant"
                >
                  <div>
                    <p className="font-medium text-text-primary">
                      {booking.requested_date}
                      {booking.requested_time ? ` at ${booking.requested_time.slice(0, 5)}` : ""}
                    </p>
                    <p className="mt-1 text-sm text-text-secondary">
                      {booking.customer_display_name ?? "Customer"}
                      {booking.service_name ? ` · ${booking.service_name}` : ""}
                    </p>
                  </div>
                  <span className="rounded-full border border-border px-3 py-1 text-xs font-medium text-text-primary">
                    {BOOKING_STATUS_LABELS[booking.status]}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}

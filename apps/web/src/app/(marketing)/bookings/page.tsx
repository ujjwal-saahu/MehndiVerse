import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { BOOKING_STATUS_LABELS } from "@/lib/booking-types";
import type { BookingSummaryData } from "@/lib/booking-types";
import { backendFetch } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function MyBookingsPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch("/bookings/mine", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const bookings = response.ok ? ((await response.json()) as BookingSummaryData[]) : [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">My bookings</h1>
      <p className="mt-1 text-text-secondary">
        Booking requests you&apos;ve started, submitted, or had confirmed.
      </p>

      {bookings.length === 0 ? (
        <p className="mt-8 text-sm text-text-secondary">
          You haven&apos;t started a booking yet. Visit an artist&apos;s profile to request one.
        </p>
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
                    {booking.artist_display_name ?? "Artist"}
                    {booking.service_name ? ` · ${booking.service_name}` : ""}
                  </p>
                  <p className="mt-1 text-sm text-text-secondary">
                    {booking.requested_date ?? "No date set yet"}
                    {booking.requested_time ? ` at ${booking.requested_time.slice(0, 5)}` : ""}
                  </p>
                </div>
                <span className="rounded-full border border-border px-3 py-1 text-xs font-medium text-text-primary">
                  {BOOKING_STATUS_LABELS[booking.status]}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

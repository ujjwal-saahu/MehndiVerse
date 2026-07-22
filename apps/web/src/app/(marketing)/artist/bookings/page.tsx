import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { BOOKING_STATUS_LABELS } from "@/lib/booking-types";
import type { BookingSummaryData } from "@/lib/booking-types";
import { backendFetch } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function ArtistBookingInboxPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch("/artist/bookings", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (response.status === 404) {
    redirect("/artist/onboarding");
  }
  const bookings = response.ok ? ((await response.json()) as BookingSummaryData[]) : [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-text-primary">Booking inbox</h1>
          <p className="mt-1 text-text-secondary">Requests customers have sent you.</p>
        </div>
        <Link
          href="/artist/bookings/calendar"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Calendar
        </Link>
      </div>

      {bookings.length === 0 ? (
        <p className="mt-8 text-sm text-text-secondary">No booking requests yet.</p>
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
                    {booking.customer_display_name ?? "Customer"}
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

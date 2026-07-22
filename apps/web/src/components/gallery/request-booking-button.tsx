"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Creates a `draft` booking against this artist and takes the customer to
 * the detail/edit page — see docs/booking-lifecycle.md#3. Replaces the
 * Phase 11 "coming soon" placeholder now that booking creation exists. */
export function RequestBookingButton({
  artistId,
  isAcceptingBookings,
}: {
  artistId: string;
  isAcceptingBookings: boolean;
}) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestBooking = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artist_profile_id: artistId }),
      });
      const body = (await response.json()) as { id: string } | { message: string };
      if (!response.ok) {
        setError((body as { message: string }).message);
        return;
      }
      router.push(`/bookings/${(body as { id: string }).id}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        disabled={!isAcceptingBookings || isLoading}
        title={isAcceptingBookings ? undefined : "This artist isn't accepting bookings right now."}
        onClick={() => void requestBooking()}
        className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isAcceptingBookings ? "Request a booking" : "Not accepting bookings"}
      </button>
      {error ? <p className="text-xs text-danger">{error}</p> : null}
    </div>
  );
}

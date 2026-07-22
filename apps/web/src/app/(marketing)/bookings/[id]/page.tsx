import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ArtistPublicProfileData } from "@/lib/artist-directory-types";
import type { BookingDetailData } from "@/lib/booking-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { BookingDetailView } from "./booking-detail-view";

interface CurrentUser {
  id: string;
}

export default async function BookingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const [bookingResponse, userResponse] = await Promise.all([
    backendFetch(`/bookings/${id}`, { headers: { Authorization: `Bearer ${accessToken}` } }),
    backendFetch("/auth/me", { headers: { Authorization: `Bearer ${accessToken}` } }),
  ]);

  if (bookingResponse.status === 404) {
    notFound();
  }
  if (!bookingResponse.ok || !userResponse.ok) {
    redirect("/bookings");
  }

  const booking = (await bookingResponse.json()) as BookingDetailData;
  const currentUser = (await userResponse.json()) as CurrentUser;
  const viewerIsCustomer = booking.customer_id === currentUser.id;

  const artistResponse = await backendFetch(`/artists/${booking.artist_profile_id}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const artist = artistResponse.ok
    ? ((await artistResponse.json()) as ArtistPublicProfileData)
    : null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <BookingDetailView
        initialBooking={booking}
        viewerIsCustomer={viewerIsCustomer}
        services={artist?.services ?? []}
      />
    </div>
  );
}

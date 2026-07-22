import Image from "next/image";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { DesignCard } from "@/components/design-grid/design-card";
import { ReportButton } from "@/components/feedback/report-button";
import { CheckAvailabilityWidget } from "@/components/gallery/check-availability-widget";
import { FollowButton } from "@/components/gallery/follow-button";
import { RequestBookingButton } from "@/components/gallery/request-booking-button";
import { ReviewsSection } from "@/components/gallery/reviews-section";
import { backendFetch } from "@/lib/backend";
import type { ArtistPublicProfileData } from "@/lib/artist-directory-types";
import { DAY_NAMES } from "@/lib/artist-directory-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

function formatTime(value: string): string {
  const [hours, minutes] = value.split(":");
  return `${hours}:${minutes}`;
}

function formatMoney(amount: number | null, currency: string): string | null {
  if (amount === null) return null;
  return `${currency} ${amount.toLocaleString()}`;
}

export default async function ArtistProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch(`/artists/${id}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (response.status === 404) {
    notFound();
  }
  if (!response.ok) {
    redirect("/artists");
  }
  const artist = (await response.json()) as ArtistPublicProfileData;

  return (
    <div className="mx-auto max-w-4xl px-4 pb-16 sm:px-6">
      <div className="relative -mx-4 h-48 overflow-hidden bg-surface-variant sm:-mx-6 sm:h-64">
        {artist.cover_image_url ? (
          <Image src={artist.cover_image_url} alt="" fill className="object-cover" />
        ) : null}
      </div>

      <div className="relative -mt-12 flex items-end gap-4 px-2">
        <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-full border-4 border-background bg-surface-variant">
          {artist.profile_image_url ? (
            <Image
              src={artist.profile_image_url}
              alt=""
              fill
              sizes="96px"
              className="object-cover"
            />
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-semibold text-text-primary">
              {artist.display_name}
            </h1>
            {artist.is_verified ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-info-surface px-2 py-0.5 text-xs font-medium text-info">
                ✓ Verified
              </span>
            ) : null}
          </div>
          {artist.headline ? <p className="mt-1 text-text-secondary">{artist.headline}</p> : null}
          <p className="mt-1 text-sm text-text-secondary">
            {[artist.city, artist.country].filter(Boolean).join(", ")}
            {artist.years_experience ? ` · ${artist.years_experience} yrs experience` : ""}
          </p>
          <p className="mt-1 text-sm text-text-secondary">
            {artist.rating_count > 0
              ? `★ ${artist.rating_average.toFixed(1)} (${artist.rating_count} reviews)`
              : "No reviews yet"}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <FollowButton
            artistId={artist.id}
            initialIsFollowed={artist.is_followed}
            initialFollowerCount={artist.follower_count}
          />
          <RequestBookingButton
            artistId={artist.id}
            isAcceptingBookings={artist.is_accepting_bookings}
          />
          <ReportButton
            endpoint={`/api/users/${artist.user_id}/report`}
            label="Report artist"
            promptMessage="Why are you reporting this artist?"
          />
        </div>
      </div>

      {artist.bio ? <p className="mt-6 text-text-primary">{artist.bio}</p> : null}

      {artist.service_areas.length > 0 || artist.languages.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-6 text-sm text-text-secondary">
          {artist.service_areas.length > 0 ? (
            <p>
              <span className="font-medium text-text-primary">Service areas: </span>
              {artist.service_areas.join(", ")}
            </p>
          ) : null}
          {artist.languages.length > 0 ? (
            <p>
              <span className="font-medium text-text-primary">Languages: </span>
              {artist.languages.join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}

      {artist.services.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-lg font-semibold text-text-primary">Services</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {artist.services.map((service) => (
              <div key={service.id} className="rounded-xl border border-border bg-surface p-4">
                <p className="font-medium text-text-primary">{service.name}</p>
                {service.description ? (
                  <p className="mt-1 text-sm text-text-secondary">{service.description}</p>
                ) : null}
                <p className="mt-2 text-sm text-text-primary">
                  {service.pricing_type === "fixed"
                    ? formatMoney(service.price_amount, service.currency)
                    : service.pricing_type === "range"
                      ? `${formatMoney(service.price_min, service.currency)} – ${formatMoney(service.price_max, service.currency)}`
                      : "Custom quote"}
                  {service.duration_minutes ? ` · ${service.duration_minutes} min` : ""}
                </p>
                {service.deposit_required ? (
                  <p className="mt-1 text-xs text-text-secondary">
                    Deposit required
                    {service.deposit_amount
                      ? `: ${formatMoney(service.deposit_amount, service.currency)}`
                      : ""}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <CheckAvailabilityWidget artistId={artist.id} services={artist.services} />

      {artist.availability_preview.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-lg font-semibold text-text-primary">Availability</h2>
          <ul className="mt-3 flex flex-wrap gap-2 text-sm text-text-secondary">
            {artist.availability_preview.map((slot, index) => (
              <li key={index} className="rounded-full border border-border px-3 py-1">
                {DAY_NAMES[slot.day_of_week]} {formatTime(slot.start_time)}–
                {formatTime(slot.end_time)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-text-primary">Portfolio</h2>
          {artist.portfolio_count > artist.portfolio_preview.length ? (
            <Link
              href={`/artists/${artist.id}/portfolio`}
              className="text-sm font-medium text-primary hover:underline"
            >
              View all {artist.portfolio_count}
            </Link>
          ) : null}
        </div>
        {artist.portfolio_preview.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">No published designs yet.</p>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {artist.portfolio_preview.map((design) => (
              <DesignCard
                key={design.id}
                design={{
                  id: design.id,
                  title: design.title,
                  imageUrl: design.thumbnail_url,
                  href: `/designs/${design.id}`,
                }}
              />
            ))}
          </div>
        )}
      </section>

      <ReviewsSection artistProfileId={artist.id} />
    </div>
  );
}

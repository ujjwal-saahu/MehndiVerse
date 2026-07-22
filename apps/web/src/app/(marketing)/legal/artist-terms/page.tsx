import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Artist Terms | MehndiVerse" };

export default function ArtistTermsPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Artist Terms</h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">Verification</h2>
        <p className="text-text-secondary">
          Offering paid services requires completing artist verification (identity and, where
          applicable, business documents). Staff review submissions; you&apos;ll be notified of
          approval, rejection, or a request for more information.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Bookings, payouts, and commission
        </h2>
        <p className="text-text-secondary">
          You set your own services, pricing, and availability. MehndiVerse deducts a platform
          commission from each completed booking before payout; the exact rate is shown in your
          artist dashboard before you publish a service. Payouts follow the schedule described in
          your dashboard.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Cancellations and disputes
        </h2>
        <p className="text-text-secondary">
          Cancellations are governed by the{" "}
          <a href="/legal/cancellation-policy" className="text-primary hover:underline">
            Cancellation Policy
          </a>
          . Customer disputes go through staff-mediated resolution before any refund/payout
          adjustment is made.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Portfolio and conduct
        </h2>
        <p className="text-text-secondary">
          Portfolio uploads must be your own work and follow the{" "}
          <a href="/legal/community-guidelines" className="text-primary hover:underline">
            Community Guidelines
          </a>
          . Repeated policy violations may lead to suspension of your verified-artist status.
        </p>
      </section>
    </div>
  );
}

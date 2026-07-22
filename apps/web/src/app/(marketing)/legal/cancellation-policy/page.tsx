import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Cancellation Policy | MehndiVerse" };

export default function CancellationPolicyPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Cancellation Policy</h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Cancelling a booking
        </h2>
        <p className="text-text-secondary">
          Either the customer or the artist can cancel a booking any time before it&apos;s marked
          completed, from the booking&apos;s detail page. Cancelling records the reason and notifies
          the other party.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Deposits and cancellation fees
        </h2>
        <p className="text-text-secondary">
          <strong>This section is a placeholder pending a business decision.</strong> The platform
          does not currently apply an automated cancellation-fee schedule (e.g. &quot;full refund if
          cancelled 48+ hours ahead&quot;) — every cancellation involving a paid deposit is reviewed
          individually against our{" "}
          <a href="/legal/refund-policy" className="text-primary hover:underline">
            Refund Policy
          </a>
          . A concrete fee schedule, once decided, should be documented here and reflected in the
          booking flow&apos;s own copy before this notice is removed.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Artist-initiated cancellations
        </h2>
        <p className="text-text-secondary">
          Repeated last-minute cancellations by an artist may affect their verification standing —
          see the{" "}
          <a href="/legal/artist-terms" className="text-primary hover:underline">
            Artist Terms
          </a>
          .
        </p>
      </section>
    </div>
  );
}

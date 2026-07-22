import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Refund Policy | MehndiVerse" };

export default function RefundPolicyPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Refund Policy</h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Requesting a refund
        </h2>
        <p className="text-text-secondary">
          After a booking is marked completed, you can raise a refund request from the booking
          detail page. This puts the booking into a staff-reviewed state — nothing is refunded
          automatically.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">How refunds work</h2>
        <p className="text-text-secondary">
          Refunds are processed back to your original Razorpay payment method. Our payment
          reconciliation job checks daily for any refund that Razorpay confirmed but our system
          didn&apos;t record, so a confirmed refund is never silently lost.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          What isn&apos;t covered yet
        </h2>
        <p className="text-text-secondary">
          <strong>Placeholder pending a business decision:</strong> there is currently no automated
          eligibility rule (e.g. a time window or percentage schedule) — every request is reviewed
          individually by staff. See the{" "}
          <a href="/legal/cancellation-policy" className="text-primary hover:underline">
            Cancellation Policy
          </a>{" "}
          for cancelling before completion instead.
        </p>
      </section>
    </div>
  );
}

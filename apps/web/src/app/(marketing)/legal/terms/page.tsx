import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Terms of Service | MehndiVerse" };

export default function TermsOfServicePage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Terms of Service</h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          1. Using MehndiVerse
        </h2>
        <p className="text-text-secondary">
          MehndiVerse connects customers with independent mehndi artists. Customers browse designs
          and request bookings; artists accept, quote, and fulfil them. We are a marketplace, not a
          party to the service agreement between customer and artist, except where these terms say
          otherwise (e.g. payment handling).
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          2. Accounts and eligibility
        </h2>
        <p className="text-text-secondary">
          You must provide accurate information and are responsible for activity under your account.
          Artists additionally agree to the{" "}
          <a href="/legal/artist-terms" className="text-primary hover:underline">
            Artist Terms
          </a>
          .
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          3. Bookings and payments
        </h2>
        <p className="text-text-secondary">
          Bookings, deposits, and payments are governed by our{" "}
          <a href="/legal/cancellation-policy" className="text-primary hover:underline">
            Cancellation Policy
          </a>{" "}
          and{" "}
          <a href="/legal/refund-policy" className="text-primary hover:underline">
            Refund Policy
          </a>
          . Payments are processed by Razorpay; we never store your card or bank details.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          4. Content and conduct
        </h2>
        <p className="text-text-secondary">
          Uploaded designs, reviews, and messages must comply with our{" "}
          <a href="/legal/community-guidelines" className="text-primary hover:underline">
            Community Guidelines
          </a>
          . We may remove content or suspend accounts that violate them.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          5. AI-assisted features
        </h2>
        <p className="text-text-secondary">
          Some design suggestions and previews use AI processing — see the{" "}
          <a href="/legal/ai-disclosure" className="text-primary hover:underline">
            AI-content disclosure
          </a>{" "}
          for what that means for your uploads.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          6. Termination and account deletion
        </h2>
        <p className="text-text-secondary">
          You may delete your account at any time from account settings. Some records (completed
          payments, audit logs) are retained after deletion for legal and financial-compliance
          reasons — see our Privacy Policy&apos;s data-retention section.
        </p>
      </section>
    </div>
  );
}

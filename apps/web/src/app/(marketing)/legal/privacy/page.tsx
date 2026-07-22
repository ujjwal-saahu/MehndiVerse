import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Privacy Policy | MehndiVerse" };

export default function PrivacyPolicyPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Privacy Policy</h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">1. What we collect</h2>
        <p className="text-text-secondary">
          Account details (email, phone), profile information you choose to add (display name, bio,
          city, avatar), booking and payment records, messages exchanged through the platform,
          uploaded designs and portfolio images, verification documents submitted by artists, and
          usage data (e.g. which designs you view) where you have given analytics consent. See{" "}
          <a href="/legal/ai-disclosure" className="text-primary hover:underline">
            AI-content disclosure
          </a>{" "}
          for how AI-processed images are handled.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">2. How we use it</h2>
        <p className="text-text-secondary">
          To operate bookings, payments, messaging, and moderation; to personalize your feed only
          where you&apos;ve consented to analytics tracking; to detect fraud and abuse; and to
          comply with tax and financial record-keeping obligations.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">3. Data retention</h2>
        <p className="text-text-secondary">
          See the retention table in our data-retention documentation
          (docs/legal-and-support.md#data-retention-categories) for how long each category of data
          is kept, including why financial and audit records are retained even after account
          deletion.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          4. Third-party processors
        </h2>
        <p className="text-text-secondary">
          We share data with a small number of processors strictly to operate the service: Supabase
          (authentication, database, file storage), Razorpay (payment processing). See{" "}
          <a href="/legal/cookies" className="text-primary hover:underline">
            our Cookie Policy
          </a>{" "}
          for analytics.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">5. Your rights</h2>
        <p className="text-text-secondary">
          You can request a copy of your data at any time from{" "}
          <a href="/account/data-export" className="text-primary hover:underline">
            Account → Data export
          </a>
          , and request account deletion from Account settings. See{" "}
          <a href="/support/contact" className="text-primary hover:underline">
            Contact support
          </a>{" "}
          for any other privacy request.
        </p>
      </section>
    </div>
  );
}

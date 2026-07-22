import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Community Guidelines | MehndiVerse" };

export default function CommunityGuidelinesPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        Community Guidelines
      </h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          What we expect from everyone
        </h2>
        <ul className="list-disc pl-5 text-text-secondary">
          <li>Be respectful in messages, reviews, and comments — no harassment or hate speech.</li>
          <li>Only upload designs and photos you have the rights to share.</li>
          <li>Don&apos;t impersonate another person or artist business.</li>
          <li>
            Don&apos;t attempt to move payments outside the platform to avoid fees or protections.
          </li>
        </ul>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Reporting and enforcement
        </h2>
        <p className="text-text-secondary">
          Use the &quot;Report&quot; action on a design, comment, message, or profile — every report
          enters a staff moderation queue. Violations may result in content removal, warnings, or
          account suspension. If you believe a decision was made in error, use{" "}
          <a href="/support/contact" className="text-primary hover:underline">
            Contact support
          </a>
          .
        </p>
      </section>
    </div>
  );
}

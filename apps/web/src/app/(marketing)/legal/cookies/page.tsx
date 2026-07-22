import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "Cookie Policy | MehndiVerse" };

export default function CookiePolicyPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Cookie Policy</h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Strictly necessary cookies
        </h2>
        <p className="text-text-secondary">
          Session cookies that keep you signed in and protect against cross-site request forgery.
          These are required for the app to work and are not affected by the cookie-consent
          banner&apos;s choice.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">Analytics consent</h2>
        <p className="text-text-secondary">
          We record anonymous usage events (e.g. which designs are viewed) to power recommendations
          and analytics. When you&apos;re signed in, we only attach this activity to your account if
          you&apos;ve turned on &quot;Personalization and analytics&quot; in Account → Privacy
          settings — the cookie-consent banner sets this same preference. If you decline, anonymous
          aggregate events may still be recorded, but never linked to your account.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          No third-party advertising cookies
        </h2>
        <p className="text-text-secondary">
          MehndiVerse does not currently use third-party advertising or cross-site tracking cookies.
        </p>
      </section>
    </div>
  );
}

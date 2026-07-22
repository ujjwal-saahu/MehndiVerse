import { LegalReviewNotice } from "@/components/legal/legal-review-notice";

export const metadata = { title: "AI-Content Disclosure | MehndiVerse" };

export default function AiDisclosurePage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        AI-Content Disclosure
      </h1>
      <p className="text-sm text-text-secondary">Last updated: 21 July 2026 (draft)</p>
      <LegalReviewNotice />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          AI design generation
        </h2>
        <p className="text-text-secondary">
          The AI Design Assistant generates a design image from a form you fill in (style, occasion,
          body part, etc.) — it is never a human artist&apos;s work. Every generated result is
          labeled, in the app and in any message it&apos;s shared through, with:{" "}
          <em>&quot;AI-generated design — not created by a human artist.&quot;</em> Generated
          results never become catalog listings or get attributed to any artist.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          What kind of &quot;AI&quot; this is today
        </h2>
        <p className="text-text-secondary">
          Today&apos;s default provider is a deterministic, rule-based image renderer — not a
          trained generative model. The same request always produces the same design. The system is
          built so a real hosted model can be swapped in later without changing how results are
          labeled or moderated.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Automatic tag suggestions and duplicate detection
        </h2>
        <p className="text-text-secondary">
          When a design is uploaded to the catalog, automated tools suggest tags and check for
          likely duplicates. These are heuristic assistive tools reviewed by the artist and, for
          moderation flags, by staff — they never change what&apos;s published on their own.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Hand/foot preview is not AI
        </h2>
        <p className="text-text-secondary">
          The hand/foot design preview tool overlays a chosen design onto a photo you provide
          entirely on your own device — no image is generated or analyzed by AI, and the photo
          itself is only uploaded to our storage if you choose to save or share the result.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Consent for provider training
        </h2>
        <p className="text-text-secondary">
          The AI Design Assistant form includes an explicit, off-by-default option to allow your
          generated result to be used to improve the underlying provider. It is never turned on for
          you automatically.
        </p>
      </section>
    </div>
  );
}

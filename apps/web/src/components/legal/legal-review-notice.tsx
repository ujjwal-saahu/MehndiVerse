/** Every legal/policy placeholder page renders this — see docs/legal-and-
 * support.md. It must never be silently dropped from a page as "real"
 * legal text gets drafted in; removing it is a deliberate legal-review
 * sign-off, not a copy-editing change. */
export function LegalReviewNotice() {
  return (
    <div
      role="note"
      className="rounded-md border border-warning bg-warning-surface px-4 py-3 text-sm text-text-primary"
    >
      <strong>Draft — pending qualified legal review.</strong> This document is placeholder content
      for MehndiVerse&apos;s development and does not constitute legal advice or a binding agreement
      until reviewed and approved by qualified legal counsel.
    </div>
  );
}

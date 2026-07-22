"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "mv_cookie_consent";

/** First-run cookie/analytics consent prompt — see docs/legal-and-support.md
 * #cookie-and-analytics-consent. The choice is always saved to this
 * browser's localStorage; if the visitor happens to be signed in it's also
 * synced to `UserPreference.analytics_consent` via the existing
 * `/api/preferences` route (the same server-side gate
 * `record_event()` already checks — see docs/analytics-and-recommendations.md
 * #provide-analytics-consent-where-legally-required). A signed-out
 * visitor's choice has nothing to attach server-side to yet, so it stays
 * local until they sign in and can set it again from Account settings. */
export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Deferred to a microtask so setState never runs synchronously within
    // the effect body itself — required by the react-hooks/set-state-in-
    // effect rule (same pattern as search-view.tsx's fetchResults).
    Promise.resolve().then(() => {
      if (typeof window !== "undefined" && window.localStorage.getItem(STORAGE_KEY) === null) {
        setVisible(true);
      }
    });
  }, []);

  const respond = async (analyticsConsent: boolean) => {
    window.localStorage.setItem(STORAGE_KEY, analyticsConsent ? "accepted" : "necessary-only");
    setVisible(false);
    try {
      await fetch("/api/preferences", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analytics_consent: analyticsConsent }),
      });
    } catch {
      // Best-effort only — a signed-out visitor gets a 401 here, which is
      // expected, not an error to surface.
    }
  };

  if (!visible) return null;

  return (
    <div
      role="region"
      aria-label="Cookie consent"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface px-4 py-4 shadow-lg sm:px-6"
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-text-secondary">
          We use strictly necessary cookies to run this site, and — only with your consent —
          analytics cookies to improve recommendations. See our{" "}
          <a href="/legal/cookies" className="text-primary hover:underline">
            Cookie Policy
          </a>
          .
        </p>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => respond(false)}
            className="rounded-md border border-border px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Necessary only
          </button>
          <button
            type="button"
            onClick={() => respond(true)}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
          >
            Accept analytics
          </button>
        </div>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";

import { SUPPORTED_LOCALES, isSupportedLocale } from "@/i18n/config";
import { useTranslation } from "@/i18n/locale-provider";
import type { PreferencesData, ProfileData } from "@/lib/profile-types";

type NotificationField =
  | "email_notifications"
  | "push_notifications"
  | "sms_notifications"
  | "marketing_opt_in"
  | "analytics_consent";

export function SettingsForm({
  profile,
  preferences,
}: {
  profile: ProfileData;
  preferences: PreferencesData;
}) {
  const { t, locale: activeLocale, setLocale: setActiveLocale } = useTranslation();
  const [locale, setLocale] = useState(
    isSupportedLocale(profile.locale) ? profile.locale : activeLocale,
  );
  const [prefs, setPrefs] = useState(preferences);
  const [message, setMessage] = useState<string | null>(null);

  const onLanguageChange = async (nextLocale: string) => {
    if (!isSupportedLocale(nextLocale)) return;
    setLocale(nextLocale);
    // Persists to the account (works across devices) and to this browser's
    // cookie (works while signed out) — see i18n/locale-provider.tsx.
    setActiveLocale(nextLocale);
    await fetch("/api/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locale: nextLocale }),
    });
    setMessage(t("settings.languageUpdated"));
  };

  const onToggle = async (field: NotificationField, value: boolean) => {
    setPrefs((current) => ({ ...current, [field]: value }));
    await fetch("/api/preferences", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: value }),
    });
  };

  return (
    <div className="flex flex-col gap-8">
      {message ? (
        <p role="status" className="text-sm text-text-secondary">
          {message}
        </p>
      ) : null}

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("settings.language")}
        </h2>
        <label htmlFor="locale-select" className="sr-only">
          {t("settings.language")}
        </label>
        <select
          id="locale-select"
          value={locale}
          onChange={(event) => onLanguageChange(event.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        >
          {SUPPORTED_LOCALES.map((code) => (
            <option key={code} value={code}>
              {t(`settings.languages.${code}`)}
            </option>
          ))}
        </select>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("settings.notifications")}
        </h2>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.email_notifications}
            onChange={(event) => onToggle("email_notifications", event.target.checked)}
          />
          {t("settings.emailNotifications")}
        </label>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.push_notifications}
            onChange={(event) => onToggle("push_notifications", event.target.checked)}
          />
          {t("settings.pushNotifications")}
        </label>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.sms_notifications}
            onChange={(event) => onToggle("sms_notifications", event.target.checked)}
          />
          {t("settings.smsNotifications")}
        </label>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.marketing_opt_in}
            onChange={(event) => onToggle("marketing_opt_in", event.target.checked)}
          />
          {t("settings.marketingEmails")}
        </label>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.analytics_consent}
            onChange={(event) => onToggle("analytics_consent", event.target.checked)}
          />
          {t("settings.analyticsConsent")}
        </label>
      </section>

      <Link
        href="/account/settings/privacy"
        className="text-sm font-medium text-primary hover:underline"
      >
        {t("settings.privacySettings")}
      </Link>
    </div>
  );
}

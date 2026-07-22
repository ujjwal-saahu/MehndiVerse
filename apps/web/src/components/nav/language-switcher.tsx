"use client";

import { SUPPORTED_LOCALES, isSupportedLocale } from "@/i18n/config";
import { useTranslation } from "@/i18n/locale-provider";

/** Global language switcher, always visible in the site header/footer so a
 * visitor can change locale before ever signing in (account settings has
 * its own copy of this list that also persists the choice to the signed-in
 * user's profile — see settings-form.tsx). */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, t, setLocale } = useTranslation();

  return (
    <label className={className}>
      <span className="sr-only">{t("languageSwitcher.label")}</span>
      <select
        value={locale}
        onChange={(event) => {
          const next = event.target.value;
          if (isSupportedLocale(next)) {
            setLocale(next);
          }
        }}
        className="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary hover:bg-surface-variant focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
      >
        {SUPPORTED_LOCALES.map((code) => (
          <option key={code} value={code}>
            {t(`settings.languages.${code}`)}
          </option>
        ))}
      </select>
    </label>
  );
}

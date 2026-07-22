export const SUPPORTED_LOCALES = ["en", "hi", "ur", "ar"] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

export const RTL_LOCALES: readonly Locale[] = ["ur", "ar"];

export function isRtl(locale: Locale): boolean {
  return RTL_LOCALES.includes(locale);
}

export function isSupportedLocale(value: string | null | undefined): value is Locale {
  return !!value && (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

/** Not httpOnly on purpose: client components (the language switcher, the
 * settings form) need to read and write it directly for an instant switch,
 * without a round trip through a route handler. It only ever holds one of
 * `SUPPORTED_LOCALES` — never anything sensitive. */
export const LOCALE_COOKIE = "mv_locale";

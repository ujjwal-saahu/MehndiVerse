import { DEFAULT_LOCALE, isSupportedLocale, type Locale } from "./config";

/** Picks the locale to render with, in priority order: an explicit cookie
 * value (the user's persisted preference) beats the browser's
 * `Accept-Language` header (a first-visit guess) beats `DEFAULT_LOCALE`. */
export function resolveLocale(params: {
  cookieValue?: string | null;
  acceptLanguageHeader?: string | null;
}): Locale {
  const { cookieValue, acceptLanguageHeader } = params;
  if (isSupportedLocale(cookieValue)) {
    return cookieValue;
  }

  if (acceptLanguageHeader) {
    for (const part of acceptLanguageHeader.split(",")) {
      const tag = part.split(";")[0]?.trim().toLowerCase();
      const primary = tag?.split("-")[0];
      if (isSupportedLocale(primary)) {
        return primary;
      }
    }
  }

  return DEFAULT_LOCALE;
}

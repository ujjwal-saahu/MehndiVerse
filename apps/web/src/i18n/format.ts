import type { Locale } from "./config";

/** BCP-47 tags for `Intl` — plain locale codes (`"hi"`, `"ur"`) already
 * work, but `"ar"` defaults to Modern Standard Arabic without a region;
 * pinning region-less is intentional here since MehndiVerse doesn't yet
 * collect a user's country beyond an optional profile field. */
const INTL_TAGS: Record<Locale, string> = {
  en: "en-IN",
  hi: "hi-IN",
  ur: "ur",
  ar: "ar",
};

export function formatDate(date: Date | string | number, locale: Locale): string {
  const value = date instanceof Date ? date : new Date(date);
  return new Intl.DateTimeFormat(INTL_TAGS[locale], {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(value);
}

export function formatShortDate(date: Date | string | number, locale: Locale): string {
  const value = date instanceof Date ? date : new Date(date);
  return new Intl.DateTimeFormat(INTL_TAGS[locale], {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(value);
}

export function formatNumber(value: number, locale: Locale): string {
  return new Intl.NumberFormat(INTL_TAGS[locale]).format(value);
}

export function formatCurrency(amount: number, currency: string, locale: Locale): string {
  return new Intl.NumberFormat(INTL_TAGS[locale], {
    style: "currency",
    currency,
    currencyDisplay: "symbol",
  }).format(amount);
}

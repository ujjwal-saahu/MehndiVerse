"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { isRtl, LOCALE_COOKIE, type Locale } from "./config";
import { translate } from "./translations";

interface LocaleContextValue {
  locale: Locale;
  dir: "ltr" | "rtl";
  /** Persists `locale` to the `mv_locale` cookie, updates every component
   * subscribed via `useTranslation`/`useLocale` immediately, and refreshes
   * server components (nav labels, `<html lang/dir>`) to match. Does *not*
   * touch the signed-in user's `Profile.locale` — callers that also want
   * the preference to survive a different device (e.g. the account
   * settings form) PATCH `/api/profile` themselves alongside this call. */
  setLocale: (next: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  const setLocale = useCallback(
    (next: Locale) => {
      document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
      setLocaleState(next);
      router.refresh();
    },
    [router],
  );

  const value = useMemo<LocaleContextValue>(
    () => ({ locale, dir: isRtl(locale) ? "rtl" : "ltr", setLocale }),
    [locale, setLocale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within a LocaleProvider");
  }
  return ctx;
}

export function useTranslation(): {
  locale: Locale;
  dir: "ltr" | "rtl";
  t: (key: string, params?: Record<string, string | number>) => string;
  setLocale: (next: Locale) => void;
} {
  const { locale, dir, setLocale } = useLocale();
  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => translate(locale, key, params),
    [locale],
  );
  return { locale, dir, t, setLocale };
}

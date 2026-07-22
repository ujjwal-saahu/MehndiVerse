import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import { cookies, headers } from "next/headers";
import "./globals.css";

import { isRtl, LOCALE_COOKIE } from "@/i18n/config";
import { LocaleProvider } from "@/i18n/locale-provider";
import { resolveLocale } from "@/i18n/resolve-locale";
import { CookieConsentBanner } from "@/components/legal/cookie-consent-banner";

const fraunces = Fraunces({
  variable: "--font-display-family",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const manrope = Manrope({
  variable: "--font-body-family",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MehndiVerse",
  description: "Discover mehndi designs and book trusted artists for your bridal or everyday look.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [cookieStore, headerStore] = await Promise.all([cookies(), headers()]);
  const locale = resolveLocale({
    cookieValue: cookieStore.get(LOCALE_COOKIE)?.value,
    acceptLanguageHeader: headerStore.get("accept-language"),
  });

  return (
    <html
      lang={locale}
      dir={isRtl(locale) ? "rtl" : "ltr"}
      className={`${fraunces.variable} ${manrope.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-text-primary font-body">
        <LocaleProvider initialLocale={locale}>
          {children}
          <CookieConsentBanner />
        </LocaleProvider>
      </body>
    </html>
  );
}

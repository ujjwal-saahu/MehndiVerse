import Link from "next/link";
import { cookies } from "next/headers";

import { LanguageSwitcher } from "@/components/nav/language-switcher";
import { LOCALE_COOKIE } from "@/i18n/config";
import { resolveLocale } from "@/i18n/resolve-locale";
import { translate } from "@/i18n/translations";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Server component: reads session-cookie *presence* only (not validity) to
 * decide which call-to-action to show — this is a navigation convenience,
 * not an authorization decision (see middleware.ts for the same principle).
 * Nav labels are rendered server-side from the resolved locale cookie so
 * there's no flash of English text before a client component hydrates. */
export async function PublicNav() {
  const cookieStore = await cookies();
  const hasSession = cookieStore.has(ACCESS_TOKEN_COOKIE);
  const locale = resolveLocale({ cookieValue: cookieStore.get(LOCALE_COOKIE)?.value });
  const t = (key: string) => translate(locale, key);

  return (
    <header className="border-b border-border bg-surface">
      <nav
        aria-label="Primary"
        className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6"
      >
        <Link href="/" className="font-display text-xl font-semibold text-primary">
          MehndiVerse
        </Link>
        <div className="flex items-center gap-4">
          <Link
            href="/discover"
            className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
          >
            {t("nav.discover")}
          </Link>
          <Link
            href="/artists"
            className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
          >
            {t("nav.findArtist")}
          </Link>
          <Link
            href="/search"
            className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
          >
            {t("nav.search")}
          </Link>
          <Link
            href="/pricing"
            className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
          >
            {t("nav.pricing")}
          </Link>
          {hasSession ? (
            <>
              <Link
                href="/saved"
                className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
              >
                {t("nav.saved")}
              </Link>
              <Link
                href="/collections"
                className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
              >
                {t("nav.collections")}
              </Link>
              <Link
                href="/previews"
                className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant sm:inline-block"
              >
                {t("nav.previewStudio")}
              </Link>
            </>
          ) : null}
          <LanguageSwitcher />
          {hasSession ? (
            <Link
              href="/account"
              className="rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              {t("nav.account")}
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
              >
                {t("nav.login")}
              </Link>
              <Link
                href="/register"
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
              >
                {t("nav.signup")}
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

import Link from "next/link";
import { cookies } from "next/headers";

import { LOCALE_COOKIE } from "@/i18n/config";
import { resolveLocale } from "@/i18n/resolve-locale";
import { translate } from "@/i18n/translations";

export async function Footer() {
  const cookieStore = await cookies();
  const locale = resolveLocale({ cookieValue: cookieStore.get(LOCALE_COOKIE)?.value });
  const t = (key: string, params?: Record<string, string | number>) =>
    translate(locale, key, params);

  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-text-secondary sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>{t("footer.rights", { year: new Date().getFullYear() })}</p>
        <nav aria-label="Footer" className="flex flex-wrap gap-4">
          <Link href="/login" className="hover:text-text-primary">
            {t("footer.login")}
          </Link>
          <Link href="/register" className="hover:text-text-primary">
            {t("footer.signup")}
          </Link>
          <Link href="/legal/privacy" className="hover:text-text-primary">
            {t("footer.privacy")}
          </Link>
          <Link href="/legal/terms" className="hover:text-text-primary">
            {t("footer.terms")}
          </Link>
          <Link href="/faq" className="hover:text-text-primary">
            {t("footer.faq")}
          </Link>
          <Link href="/support/contact" className="hover:text-text-primary">
            {t("footer.contact")}
          </Link>
        </nav>
      </div>
    </footer>
  );
}

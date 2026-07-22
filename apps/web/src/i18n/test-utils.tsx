import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

import { type Locale } from "./config";
import { LocaleProvider } from "./locale-provider";

/** Test helper for any component under the `LocaleProvider` tree (directly,
 * via `useTranslation`, or transitively via `useValidationMessages`). Also
 * mock `next/navigation`'s `useRouter` in the test file — `LocaleProvider`
 * calls it to refresh server components after a locale switch. */
export function renderWithLocale(
  ui: ReactElement,
  options?: { locale?: Locale } & Omit<RenderOptions, "wrapper">,
) {
  const { locale = "en", ...renderOptions } = options ?? {};
  return render(<LocaleProvider initialLocale={locale}>{ui}</LocaleProvider>, renderOptions);
}

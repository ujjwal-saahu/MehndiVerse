"use client";

import { useTranslation } from "./locale-provider";

/** Localized strings for the handful of Zod validation rules reused across
 * `apps/web`'s forms (login, register, forgot-password, profile edit) — see
 * docs/localization-and-accessibility.md#localized-validation-messages.
 * Call inside a component (needs `LocaleProvider` context) and pass the
 * returned strings into the relevant Zod schema methods. */
export function useValidationMessages() {
  const { t } = useTranslation();
  return {
    invalidEmail: t("validation.invalidEmail"),
    passwordRequired: t("validation.passwordRequired"),
    passwordMinLength: t("validation.passwordMinLength"),
    displayNameRequired: t("validation.displayNameRequired"),
    bioTooLong: t("validation.bioTooLong"),
    invalidCountryCode: t("validation.invalidCountryCode"),
    termsMustBeAccepted: t("validation.termsMustBeAccepted"),
  };
}

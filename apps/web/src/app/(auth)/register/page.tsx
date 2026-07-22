"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/forms/form-field";
import { SubmitButton } from "@/components/forms/submit-button";
import { useTranslation } from "@/i18n/locale-provider";
import { useValidationMessages } from "@/i18n/validation-messages";

export default function RegisterPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const messages = useValidationMessages();
  const [serverError, setServerError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z.object({
        email: z.email(messages.invalidEmail),
        password: z.string().min(8, messages.passwordMinLength),
        termsAccepted: z.literal(true, messages.termsMustBeAccepted),
      }),
    [messages],
  );
  type FormValues = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const response = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: values.email,
        password: values.password,
        terms_accepted: values.termsAccepted,
      }),
    });
    const body = (await response.json()) as { message: string; needsVerification?: boolean };
    if (!response.ok) {
      setServerError(body.message);
      return;
    }
    if (body.needsVerification) {
      router.push(`/verify-email?email=${encodeURIComponent(values.email)}`);
      return;
    }
    router.push("/account");
    router.refresh();
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        {t("auth.register.title")}
      </h1>
      {serverError ? (
        <p role="alert" className="text-sm text-danger">
          {serverError}
        </p>
      ) : null}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <FormField
          label={t("auth.register.email")}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          label={t("auth.register.password")}
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <div className="flex flex-col gap-1">
          <label className="flex items-start gap-2 text-sm text-text-primary">
            <input type="checkbox" className="mt-1" {...register("termsAccepted")} />
            <span>
              {t("auth.register.termsPrefix")}{" "}
              <Link href="/legal/terms" target="_blank" className="text-primary hover:underline">
                Terms of Service
              </Link>{" "}
              {t("auth.register.termsAnd")}{" "}
              <Link href="/legal/privacy" target="_blank" className="text-primary hover:underline">
                Privacy Policy
              </Link>
            </span>
          </label>
          {errors.termsAccepted ? (
            <p role="alert" className="text-sm text-danger">
              {errors.termsAccepted.message}
            </p>
          ) : null}
        </div>
        <SubmitButton isSubmitting={isSubmitting} loadingLabel={t("auth.register.submitting")}>
          {t("auth.register.submit")}
        </SubmitButton>
      </form>
      <Link href="/login" className="text-sm text-text-secondary hover:text-text-primary">
        {t("auth.register.haveAccount")}
      </Link>
    </div>
  );
}

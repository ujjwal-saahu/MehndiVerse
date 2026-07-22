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

export default function LoginPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const messages = useValidationMessages();
  const [serverError, setServerError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z.object({
        email: z.email(messages.invalidEmail),
        password: z.string().min(1, messages.passwordRequired),
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
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const body = (await response.json()) as { message: string };
    if (!response.ok) {
      setServerError(body.message);
      return;
    }
    router.push("/account");
    router.refresh();
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        {t("auth.login.title")}
      </h1>
      {serverError ? (
        <p role="alert" className="text-sm text-danger">
          {serverError}
        </p>
      ) : null}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <FormField
          label={t("auth.login.email")}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          label={t("auth.login.password")}
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <SubmitButton isSubmitting={isSubmitting} loadingLabel={t("auth.login.submitting")}>
          {t("auth.login.submit")}
        </SubmitButton>
      </form>
      <div className="flex flex-col gap-2 text-sm text-text-secondary">
        <Link href="/forgot-password" className="hover:text-text-primary">
          {t("auth.login.forgotPassword")}
        </Link>
        <Link href="/register" className="hover:text-text-primary">
          {t("auth.login.noAccount")}
        </Link>
      </div>
    </div>
  );
}

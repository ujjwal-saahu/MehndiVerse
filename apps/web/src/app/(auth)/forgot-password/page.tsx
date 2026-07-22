"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/forms/form-field";
import { SubmitButton } from "@/components/forms/submit-button";
import { useTranslation } from "@/i18n/locale-provider";
import { useValidationMessages } from "@/i18n/validation-messages";

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const messages = useValidationMessages();
  const [message, setMessage] = useState<string | null>(null);

  const schema = useMemo(() => z.object({ email: z.email(messages.invalidEmail) }), [messages]);
  type FormValues = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    const response = await fetch("/api/auth/password-reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const body = (await response.json()) as { message: string };
    setMessage(body.message);
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        {t("auth.forgotPassword.title")}
      </h1>
      {message ? (
        <p className="text-text-secondary">{message}</p>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <FormField
            label={t("auth.forgotPassword.email")}
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register("email")}
          />
          <SubmitButton
            isSubmitting={isSubmitting}
            loadingLabel={t("auth.forgotPassword.submitting")}
          >
            {t("auth.forgotPassword.submit")}
          </SubmitButton>
        </form>
      )}
    </div>
  );
}

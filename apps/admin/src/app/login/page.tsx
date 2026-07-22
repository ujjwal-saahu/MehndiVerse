"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/forms/form-field";
import { SubmitButton } from "@/components/forms/submit-button";

const schema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type FormValues = z.infer<typeof schema>;

export default function AdminLoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
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
    router.push("/dashboard");
    router.refresh();
  };

  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-md">
        <h1 className="font-display text-2xl font-semibold text-primary">MehndiVerse Admin</h1>
        <p className="mt-2 text-sm text-text-secondary">
          Staff sign-in. Accounts are provisioned by an administrator — there is no self-service
          registration for this dashboard.
        </p>
        {serverError ? (
          <p role="alert" className="mt-4 text-sm text-danger">
            {serverError}
          </p>
        ) : null}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 flex flex-col gap-4">
          <FormField
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register("email")}
          />
          <FormField
            label="Password"
            type="password"
            autoComplete="current-password"
            error={errors.password?.message}
            {...register("password")}
          />
          <SubmitButton isSubmitting={isSubmitting} loadingLabel="Logging in…">
            Log in
          </SubmitButton>
        </form>
      </div>
    </div>
  );
}

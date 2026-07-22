"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/forms/form-field";
import { SubmitButton } from "@/components/forms/submit-button";

const CATEGORIES = [
  { value: "bug_report", label: "Something's broken (bug report)" },
  { value: "account_issue", label: "Account issue" },
  { value: "billing_issue", label: "Billing / payment issue" },
  { value: "artist_issue", label: "Issue with an artist or booking" },
  { value: "other", label: "Other" },
] as const;

const schema = z.object({
  contact_email: z.email("Enter a valid email so we can respond."),
  category: z.enum(CATEGORIES.map((option) => option.value) as [string, ...string[]]),
  subject: z.string().min(1, "Give it a short subject.").max(200),
  message: z.string().min(1, "Tell us what happened.").max(5000),
});
type FormValues = z.infer<typeof schema>;

export function SupportRequestForm({
  defaultCategory,
  prefillEmail,
}: {
  defaultCategory: (typeof CATEGORIES)[number]["value"];
  prefillEmail?: string;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { category: defaultCategory, contact_email: prefillEmail ?? "" },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const response = await fetch("/api/support/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    if (!response.ok) {
      const body = (await response.json()) as { message: string };
      setServerError(body.message);
      return;
    }
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <p role="status" className="text-text-primary">
        Thanks — we&apos;ve received your message and will follow up by email.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      {serverError ? (
        <p role="alert" className="text-sm text-danger">
          {serverError}
        </p>
      ) : null}
      <FormField
        label="Your email"
        type="email"
        autoComplete="email"
        error={errors.contact_email?.message}
        {...register("contact_email")}
      />
      <div className="flex flex-col gap-1">
        <label htmlFor="category" className="text-sm font-medium text-text-primary">
          Category
        </label>
        <select
          id="category"
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          {...register("category")}
        >
          {CATEGORIES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <FormField label="Subject" error={errors.subject?.message} {...register("subject")} />
      <div className="flex flex-col gap-1">
        <label htmlFor="message" className="text-sm font-medium text-text-primary">
          Message
        </label>
        <textarea
          id="message"
          rows={6}
          aria-invalid={Boolean(errors.message)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary focus:border-focus-ring focus:outline-none focus:ring-2 focus:ring-focus-ring"
          {...register("message")}
        />
        {errors.message ? (
          <p role="alert" className="text-sm text-danger">
            {errors.message.message}
          </p>
        ) : null}
      </div>
      <SubmitButton isSubmitting={isSubmitting}>Send</SubmitButton>
    </form>
  );
}

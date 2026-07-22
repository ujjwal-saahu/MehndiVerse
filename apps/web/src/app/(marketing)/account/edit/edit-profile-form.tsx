"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/forms/form-field";
import { SubmitButton } from "@/components/forms/submit-button";
import { useTranslation } from "@/i18n/locale-provider";
import { useValidationMessages } from "@/i18n/validation-messages";
import type { ProfileData } from "@/lib/profile-types";

const ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_AVATAR_BYTES = 5 * 1024 * 1024;

export function EditProfileForm({ profile }: { profile: ProfileData }) {
  const router = useRouter();
  const { t } = useTranslation();
  const messages = useValidationMessages();
  const [serverError, setServerError] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState(profile.avatar_url);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const schema = useMemo(
    () =>
      z.object({
        displayName: z.string().trim().min(1, messages.displayNameRequired),
        bio: z.string().trim().max(1000, messages.bioTooLong).optional(),
        city: z.string().trim().max(120).optional(),
        country: z
          .string()
          .trim()
          .regex(/^([A-Za-z]{2})?$/, messages.invalidCountryCode)
          .optional(),
      }),
    [messages],
  );
  type FormValues = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      displayName: profile.display_name,
      bio: profile.bio ?? "",
      city: profile.city ?? "",
      country: profile.country ?? "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const body: Record<string, string> = { display_name: values.displayName };
    if (values.bio) body.bio = values.bio;
    if (values.city) body.city = values.city;
    if (values.country) body.country = values.country;

    const response = await fetch("/api/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const responseBody = (await response.json()) as { message?: string };
    if (!response.ok) {
      setServerError(responseBody.message ?? t("profileEdit.genericSaveError"));
      return;
    }
    router.push("/account");
    router.refresh();
  };

  const onAvatarSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setAvatarError(null);

    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
      setAvatarError(t("profileEdit.avatarInvalidType"));
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setAvatarError(t("profileEdit.avatarTooLarge"));
      return;
    }

    setIsUploadingAvatar(true);
    try {
      const formData = new FormData();
      formData.set("file", file);
      const response = await fetch("/api/profile/avatar", { method: "POST", body: formData });
      const body = (await response.json()) as { avatar_url?: string; message?: string };
      if (!response.ok) {
        setAvatarError(body.message ?? t("profileEdit.genericAvatarError"));
        return;
      }
      setAvatarUrl(body.avatar_url ?? null);
    } finally {
      setIsUploadingAvatar(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full bg-surface-variant">
          {avatarUrl ? (
            <Image src={avatarUrl} alt="" fill sizes="64px" className="object-cover" />
          ) : null}
        </div>
        <div>
          <label className="cursor-pointer text-sm font-medium text-primary hover:underline">
            {isUploadingAvatar ? t("profileEdit.uploading") : t("profileEdit.changePhoto")}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              disabled={isUploadingAvatar}
              onChange={onAvatarSelected}
            />
          </label>
          {avatarError ? (
            <p role="alert" className="text-sm text-danger">
              {avatarError}
            </p>
          ) : null}
        </div>
      </div>

      {serverError ? (
        <p role="alert" className="text-sm text-danger">
          {serverError}
        </p>
      ) : null}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <FormField
          label={t("profileEdit.displayName")}
          error={errors.displayName?.message}
          {...register("displayName")}
        />
        <FormField label={t("profileEdit.bio")} error={errors.bio?.message} {...register("bio")} />
        <FormField
          label={t("profileEdit.city")}
          error={errors.city?.message}
          {...register("city")}
        />
        <FormField
          label={t("profileEdit.country")}
          error={errors.country?.message}
          {...register("country")}
        />
        <SubmitButton isSubmitting={isSubmitting} loadingLabel={t("profileEdit.saving")}>
          {t("profileEdit.save")}
        </SubmitButton>
      </form>
    </div>
  );
}

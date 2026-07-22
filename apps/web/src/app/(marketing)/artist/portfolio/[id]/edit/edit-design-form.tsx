"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SubmitButton } from "@/components/forms/submit-button";
import type { CategoryData, DesignDetailData, DesignImageData } from "@/lib/gallery-types";
import { mutateJson } from "@/lib/gallery-client";

const DIFFICULTIES = ["beginner", "intermediate", "advanced"] as const;
const BODY_PLACEMENTS = ["hand", "foot", "arm", "back", "other"] as const;

export function EditDesignForm({
  initialDesign,
  categories,
  canSetPremium,
}: {
  initialDesign: DesignDetailData;
  categories: CategoryData[];
  canSetPremium: boolean;
}) {
  const router = useRouter();
  const [design, setDesign] = useState(initialDesign);
  const [title, setTitle] = useState(design.title);
  const [description, setDescription] = useState(design.description ?? "");
  const [difficultyLevel, setDifficultyLevel] = useState(design.difficulty_level ?? "");
  const [bodyPlacement, setBodyPlacement] = useState(design.body_placement ?? "");
  const [categoryIds, setCategoryIds] = useState<string[]>(
    design.categories.map((category) => category.id),
  );
  const [isPremium, setIsPremium] = useState(design.is_premium);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const toggleCategory = (id: string) => {
    setCategoryIds((current) =>
      current.includes(id) ? current.filter((c) => c !== id) : [...current, id],
    );
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      const updated = await mutateJson<DesignDetailData>(`/api/designs/${design.id}`, "PATCH", {
        title: title.trim(),
        description: description.trim() || null,
        difficulty_level: difficultyLevel || null,
        body_placement: bodyPlacement || null,
        is_premium: canSetPremium ? isPremium : undefined,
        category_ids: categoryIds,
      });
      setDesign(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  const togglePublish = async () => {
    setIsPublishing(true);
    setError(null);
    try {
      const nextStatus = design.status === "published" ? "draft" : "published";
      const updated = await mutateJson<DesignDetailData>(`/api/designs/${design.id}`, "PATCH", {
        status: nextStatus,
      });
      setDesign(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsPublishing(false);
    }
  };

  const archive = async () => {
    setIsArchiving(true);
    setError(null);
    try {
      const updated = await mutateJson<DesignDetailData>(
        `/api/designs/${design.id}/archive`,
        "POST",
      );
      setDesign(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsArchiving(false);
    }
  };

  const uploadImage = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const authorized = await mutateJson<{ image_id: string }>(
        `/api/designs/${design.id}/images/authorize`,
        "POST",
      );
      const formData = new FormData();
      formData.set("file", file);
      const response = await fetch(
        `/api/designs/${design.id}/images/${authorized.image_id}/upload`,
        { method: "POST", body: formData },
      );
      const body = (await response.json()) as DesignImageData & { message?: string };
      if (!response.ok) {
        throw new Error(body.message ?? "Could not upload the image.");
      }
      setDesign((current) => ({ ...current, images: [...current.images, body] }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  const canArchive = design.status === "draft" || design.status === "published";

  return (
    <div className="flex flex-col gap-8">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full bg-surface-variant px-3 py-1 text-sm font-medium text-text-secondary">
          {design.status}
        </span>
        {design.status === "draft" || design.status === "published" ? (
          <button
            type="button"
            disabled={isPublishing}
            onClick={() => void togglePublish()}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {design.status === "published" ? "Unpublish" : "Publish"}
          </button>
        ) : null}
        {canArchive ? (
          <button
            type="button"
            disabled={isArchiving}
            onClick={() => void archive()}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isArchiving ? "Archiving…" : "Archive"}
          </button>
        ) : null}
      </div>

      <section>
        <h2 className="font-display text-lg font-semibold text-text-primary">Images</h2>
        <div className="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-4">
          {design.images.map((image) => (
            <div
              key={image.id}
              className="relative aspect-square overflow-hidden rounded-md bg-surface-variant"
            >
              {image.thumbnail_medium_url || image.image_url ? (
                <Image
                  src={(image.thumbnail_medium_url ?? image.image_url) as string}
                  alt=""
                  fill
                  sizes="150px"
                  className="object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-text-secondary">
                  {image.status}
                </div>
              )}
            </div>
          ))}
        </div>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={isUploading}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void uploadImage(file);
          }}
          className="mt-3 text-sm text-text-secondary"
        />
      </section>

      <form onSubmit={save} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Title</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Description</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Difficulty</span>
          <select
            value={difficultyLevel}
            onChange={(event) => setDifficultyLevel(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          >
            <option value="">Not specified</option>
            {DIFFICULTIES.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Body placement</span>
          <select
            value={bodyPlacement}
            onChange={(event) => setBodyPlacement(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          >
            <option value="">Not specified</option>
            {BODY_PLACEMENTS.map((placement) => (
              <option key={placement} value={placement}>
                {placement}
              </option>
            ))}
          </select>
        </label>

        {categories.length > 0 ? (
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-text-primary">Categories</span>
            <div className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <label
                  key={category.id}
                  className={`cursor-pointer rounded-full border px-3 py-1 text-sm ${
                    categoryIds.includes(category.id)
                      ? "border-primary bg-primary text-text-on-primary"
                      : "border-border text-text-primary"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={categoryIds.includes(category.id)}
                    onChange={() => toggleCategory(category.id)}
                  />
                  {category.name}
                </label>
              ))}
            </div>
          </div>
        ) : null}

        <label
          className={`flex items-center gap-2 text-sm ${canSetPremium ? "text-text-primary" : "text-text-secondary"}`}
        >
          <input
            type="checkbox"
            checked={isPremium}
            disabled={!canSetPremium}
            onChange={(event) => setIsPremium(event.target.checked)}
          />
          Mark as premium
          {!canSetPremium ? " (verified artists only)" : ""}
        </label>

        <div className="flex gap-3">
          <SubmitButton isSubmitting={isSaving} loadingLabel="Saving…">
            Save changes
          </SubmitButton>
          <button
            type="button"
            onClick={() => router.push("/artist/portfolio")}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Back to portfolio
          </button>
        </div>
      </form>
    </div>
  );
}

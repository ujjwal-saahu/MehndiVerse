"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SubmitButton } from "@/components/forms/submit-button";
import type { CategoryData, DesignDetailData } from "@/lib/gallery-types";
import { mutateJson } from "@/lib/gallery-client";

const DIFFICULTIES = ["beginner", "intermediate", "advanced"] as const;
const BODY_PLACEMENTS = ["hand", "foot", "arm", "back", "other"] as const;

export function CreateDesignForm({
  categories,
  canSetPremium,
}: {
  categories: CategoryData[];
  canSetPremium: boolean;
}) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficultyLevel, setDifficultyLevel] = useState("");
  const [bodyPlacement, setBodyPlacement] = useState("");
  const [categoryIds, setCategoryIds] = useState<string[]>([]);
  const [isPremium, setIsPremium] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleCategory = (id: string) => {
    setCategoryIds((current) =>
      current.includes(id) ? current.filter((c) => c !== id) : [...current, id],
    );
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const created = await mutateJson<DesignDetailData>("/api/designs", "POST", {
        title: title.trim(),
        description: description.trim() || undefined,
        difficulty_level: difficultyLevel || undefined,
        body_placement: bodyPlacement || undefined,
        is_premium: canSetPremium ? isPremium : undefined,
        category_ids: categoryIds,
      });
      router.push(`/artist/portfolio/${created.id}/edit`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

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

      {canSetPremium ? (
        <label className="flex items-center gap-2 text-sm text-text-primary">
          <input
            type="checkbox"
            checked={isPremium}
            onChange={(event) => setIsPremium(event.target.checked)}
          />
          Mark as premium
        </label>
      ) : null}

      <SubmitButton isSubmitting={isSubmitting} loadingLabel="Creating…">
        Create design
      </SubmitButton>
    </form>
  );
}

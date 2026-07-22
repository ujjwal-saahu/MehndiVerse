"use client";

import { useState } from "react";

import type { LikeStatusData, SaveStatusData } from "@/lib/collection-types";
import { mutateJson } from "@/lib/gallery-client";

interface LikeSaveButtonsProps {
  designId: string;
  initialIsLiked: boolean;
  initialLikeCount: number;
  initialIsSaved: boolean;
  initialSaveCount: number;
}

/** Like/save toggles on the design-detail view — see
 * docs/engagement-and-collections.md#optimistic-ui. Both buttons flip
 * immediately on click (optimistic) and roll back to the pre-click state if
 * the backend call fails, rather than leaving the UI in a state the server
 * never actually reached. */
export function LikeSaveButtons({
  designId,
  initialIsLiked,
  initialLikeCount,
  initialIsSaved,
  initialSaveCount,
}: LikeSaveButtonsProps) {
  const [isLiked, setIsLiked] = useState(initialIsLiked);
  const [likeCount, setLikeCount] = useState(initialLikeCount);
  const [likeError, setLikeError] = useState<string | null>(null);
  const [isLikePending, setIsLikePending] = useState(false);

  const [isSaved, setIsSaved] = useState(initialIsSaved);
  const [saveCount, setSaveCount] = useState(initialSaveCount);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSavePending, setIsSavePending] = useState(false);

  const toggleLike = () => {
    if (isLikePending) return;
    const previousLiked = isLiked;
    const previousCount = likeCount;
    const nextLiked = !isLiked;

    setIsLiked(nextLiked);
    setLikeCount(previousCount + (nextLiked ? 1 : -1));
    setLikeError(null);
    setIsLikePending(true);

    mutateJson<LikeStatusData>(`/api/designs/${designId}/like`, nextLiked ? "POST" : "DELETE")
      .then((data) => {
        setIsLiked(data.liked);
        setLikeCount(data.like_count);
      })
      .catch((error: Error) => {
        setIsLiked(previousLiked);
        setLikeCount(previousCount);
        setLikeError(error.message);
      })
      .finally(() => setIsLikePending(false));
  };

  const toggleSave = () => {
    if (isSavePending) return;
    const previousSaved = isSaved;
    const previousCount = saveCount;
    const nextSaved = !isSaved;

    setIsSaved(nextSaved);
    setSaveCount(previousCount + (nextSaved ? 1 : -1));
    setSaveError(null);
    setIsSavePending(true);

    mutateJson<SaveStatusData>(`/api/designs/${designId}/save`, nextSaved ? "POST" : "DELETE")
      .then((data) => {
        setIsSaved(data.saved);
        setSaveCount(data.save_count);
      })
      .catch((error: Error) => {
        setIsSaved(previousSaved);
        setSaveCount(previousCount);
        setSaveError(error.message);
      })
      .finally(() => setIsSavePending(false));
  };

  const buttonClass = (active: boolean) =>
    `flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60 ${
      active
        ? "border-primary bg-primary text-text-on-primary"
        : "border-border bg-background text-text-primary hover:bg-surface-variant"
    }`;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        aria-pressed={isLiked}
        disabled={isLikePending}
        onClick={toggleLike}
        className={buttonClass(isLiked)}
      >
        <span aria-hidden="true">{isLiked ? "♥" : "♡"}</span>
        {isLiked ? "Liked" : "Like"}
        <span className="text-xs opacity-80">{likeCount}</span>
      </button>

      <button
        type="button"
        aria-pressed={isSaved}
        disabled={isSavePending}
        onClick={toggleSave}
        className={buttonClass(isSaved)}
      >
        <span aria-hidden="true">{isSaved ? "🔖" : "📑"}</span>
        {isSaved ? "Saved" : "Save"}
        <span className="text-xs opacity-80">{saveCount}</span>
      </button>

      {likeError ? (
        <p role="alert" className="text-sm text-danger">
          {likeError}
        </p>
      ) : null}
      {saveError ? (
        <p role="alert" className="text-sm text-danger">
          {saveError}
        </p>
      ) : null}
    </div>
  );
}

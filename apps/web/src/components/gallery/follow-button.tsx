"use client";

import { useState } from "react";

import { mutateJson, sendRequest } from "@/lib/gallery-client";

/** Follow/unfollow foundation — see docs/artist-directory.md#follow-foundation.
 * Optimistic like every other toggle in this app (see
 * docs/engagement-and-collections.md#optimistic-ui-with-rollback): flips
 * immediately, rolls back on failure. */
export function FollowButton({
  artistId,
  initialIsFollowed,
  initialFollowerCount,
}: {
  artistId: string;
  initialIsFollowed: boolean;
  initialFollowerCount: number;
}) {
  const [isFollowed, setIsFollowed] = useState(initialIsFollowed);
  const [followerCount, setFollowerCount] = useState(initialFollowerCount);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = async () => {
    const previousFollowed = isFollowed;
    const previousCount = followerCount;
    setIsSubmitting(true);
    setError(null);
    setIsFollowed(!previousFollowed);
    setFollowerCount(previousFollowed ? previousCount - 1 : previousCount + 1);

    try {
      if (previousFollowed) {
        await sendRequest(`/api/artists/${artistId}/follow`, "DELETE");
      } else {
        await mutateJson(`/api/artists/${artistId}/follow`, "POST");
      }
    } catch (err) {
      setIsFollowed(previousFollowed);
      setFollowerCount(previousCount);
      setError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        disabled={isSubmitting}
        onClick={() => void toggle()}
        className={
          isFollowed
            ? "rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
            : "rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
        }
      >
        {isFollowed ? "Following" : "Follow"} · {followerCount}
      </button>
      {error ? (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}

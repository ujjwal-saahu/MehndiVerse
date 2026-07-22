"use client";

import { useEffect, useState } from "react";

import type { ReviewListData } from "@/lib/community-types";
import { fetchJson } from "@/lib/gallery-client";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ReviewListData };

export function ReviewsSection({ artistProfileId }: { artistProfileId: string }) {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    fetchJson<ReviewListData>(`/api/artists/${artistProfileId}/reviews`)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  }, [artistProfileId]);

  return (
    <section className="mt-8">
      <h2 className="font-display text-lg font-semibold text-text-primary">Reviews</h2>

      {state.status === "loading" ? (
        <p className="mt-3 text-sm text-text-secondary">Loading reviews…</p>
      ) : state.status === "error" ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          {state.message}
        </p>
      ) : state.data.items.length === 0 ? (
        <p className="mt-3 text-sm text-text-secondary">No reviews yet.</p>
      ) : (
        <div className="mt-4 flex flex-col gap-4">
          {state.data.items.map((review) => (
            <div key={review.id} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-text-primary">
                  {"★".repeat(review.rating)}
                  {"☆".repeat(5 - review.rating)}
                </span>
                <span className="text-xs text-text-secondary">
                  {new Date(review.created_at).toLocaleDateString()}
                </span>
              </div>
              {review.body ? <p className="mt-2 text-sm text-text-primary">{review.body}</p> : null}
              <p className="mt-2 text-xs text-text-secondary">
                {review.customer_display_name ?? "A customer"}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

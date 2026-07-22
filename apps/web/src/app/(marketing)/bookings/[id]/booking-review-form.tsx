"use client";

import { useState } from "react";

interface BookingReviewFormProps {
  bookingId: string;
}

/** Shown to the customer once a booking is completed — see
 * docs/community-and-trust.md#3-review-a-completed-booking. Submitting
 * twice for the same booking is rejected by the backend with 409 (one
 * review per completed booking), which surfaces here as a plain error
 * message rather than the app tracking "already reviewed" state itself. */
export function BookingReviewForm({ bookingId }: BookingReviewFormProps) {
  const [rating, setRating] = useState(0);
  const [body, setBody] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDone, setIsDone] = useState(false);

  if (isDone) {
    return (
      <section className="mt-6 rounded-xl border border-border bg-surface p-4">
        <p className="text-sm text-text-primary">Thanks for your review!</p>
      </section>
    );
  }

  const submit = () => {
    if (rating < 1) return;
    setIsSubmitting(true);
    setError(null);
    fetch(`/api/bookings/${bookingId}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, body: body.trim() || null }),
    })
      .then(async (response) => {
        const json = (await response.json()) as { message?: string };
        if (!response.ok) {
          setError(json.message ?? "Something went wrong. Please try again.");
          return;
        }
        setIsDone(true);
      })
      .finally(() => setIsSubmitting(false));
  };

  return (
    <section className="mt-6 rounded-xl border border-border bg-surface p-4">
      <h2 className="font-medium text-text-primary">Leave a review</h2>
      <div className="mt-3 flex items-center gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={rating === value}
            aria-label={`${value} star${value === 1 ? "" : "s"}`}
            onClick={() => setRating(value)}
            className="text-2xl leading-none"
          >
            {value <= rating ? "★" : "☆"}
          </button>
        ))}
      </div>
      <textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder="Tell others about your experience (optional)"
        rows={3}
        maxLength={3000}
        className="mt-3 w-full rounded-md border border-border bg-background p-2 text-sm text-text-primary"
      />
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={submit}
          disabled={isSubmitting || rating < 1}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-on-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Submitting…" : "Submit review"}
        </button>
        {error ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}

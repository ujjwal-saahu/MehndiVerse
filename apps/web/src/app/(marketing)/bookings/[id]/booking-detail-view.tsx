"use client";

import Image from "next/image";
import { useState } from "react";

import type { ArtistServiceData } from "@/lib/artist-directory-types";
import { BOOKING_STATUS_LABELS, EVENT_TYPE_LABELS } from "@/lib/booking-types";
import type { BookingDetailData, EventType, LocationType } from "@/lib/booking-types";

import { BookingConversation } from "./booking-conversation";
import { BookingPayments } from "./booking-payments";
import { BookingReviewForm } from "./booking-review-form";

const RESCHEDULABLE_STATUSES = new Set([
  "requested",
  "artist_reviewing",
  "quotation_sent",
  "customer_reviewing",
  "confirmed",
  "deposit_pending",
  "deposit_paid",
]);

const CANCELLABLE_STATUSES = new Set([
  "draft",
  "requested",
  "artist_reviewing",
  "quotation_sent",
  "customer_reviewing",
  "confirmed",
  "deposit_pending",
  "deposit_paid",
  "in_progress",
]);

const QUOTABLE_STATUSES = new Set([
  "requested",
  "artist_reviewing",
  "quotation_sent",
  "customer_reviewing",
]);

interface DraftForm {
  service_id: string;
  event_type: string;
  requested_date: string;
  requested_time: string;
  location_type: string;
  location_address: string;
  num_customers: string;
  design_preferences: string;
  notes: string;
  budget_min: string;
  budget_max: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
}

function toDraftForm(booking: BookingDetailData): DraftForm {
  return {
    service_id: booking.service_id ?? "",
    event_type: booking.event_type ?? "",
    requested_date: booking.requested_date ?? "",
    requested_time: booking.requested_time?.slice(0, 5) ?? "",
    location_type: booking.location_type ?? "",
    location_address: booking.location_address ?? "",
    num_customers: booking.num_customers?.toString() ?? "",
    design_preferences: booking.design_preferences ?? "",
    notes: booking.notes ?? "",
    budget_min: booking.budget_min?.toString() ?? "",
    budget_max: booking.budget_max?.toString() ?? "",
    contact_name: booking.contact_name ?? "",
    contact_email: booking.contact_email ?? "",
    contact_phone: booking.contact_phone ?? "",
  };
}

async function callAction(
  url: string,
  body?: unknown,
): Promise<{ ok: true; data: BookingDetailData } | { ok: false; message: string }> {
  const response = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = (await response.json()) as BookingDetailData | { message: string };
  if (!response.ok) {
    return { ok: false, message: (json as { message: string }).message };
  }
  return { ok: true, data: json as BookingDetailData };
}

export function BookingDetailView({
  initialBooking,
  viewerIsCustomer,
  services,
}: {
  initialBooking: BookingDetailData;
  viewerIsCustomer: boolean;
  services: ArtistServiceData[];
}) {
  const [booking, setBooking] = useState(initialBooking);
  const [draft, setDraft] = useState<DraftForm>(() => toDraftForm(initialBooking));
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [quoteAmount, setQuoteAmount] = useState("");
  const [quoteTerms, setQuoteTerms] = useState("");
  const [rescheduleDate, setRescheduleDate] = useState(booking.requested_date ?? "");
  const [rescheduleTime, setRescheduleTime] = useState(booking.requested_time?.slice(0, 5) ?? "");

  const bookableServices = services.filter((s) => s.duration_minutes !== null);

  const run = async (action: () => Promise<void>) => {
    setIsBusy(true);
    setError(null);
    try {
      await action();
    } finally {
      setIsBusy(false);
    }
  };

  const saveDraft = () =>
    run(async () => {
      const payload: Record<string, unknown> = {
        service_id: draft.service_id || null,
        event_type: draft.event_type || null,
        requested_date: draft.requested_date || null,
        requested_time: draft.requested_time ? `${draft.requested_time}:00` : null,
        location_type: draft.location_type || null,
        location_address: draft.location_address || null,
        num_customers: draft.num_customers ? Number(draft.num_customers) : null,
        design_preferences: draft.design_preferences || null,
        notes: draft.notes || null,
        budget_min: draft.budget_min ? Number(draft.budget_min) : null,
        budget_max: draft.budget_max ? Number(draft.budget_max) : null,
        contact_name: draft.contact_name || null,
        contact_email: draft.contact_email || null,
        contact_phone: draft.contact_phone || null,
      };
      const response = await fetch(`/api/bookings/${booking.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = (await response.json()) as BookingDetailData | { message: string };
      if (!response.ok) {
        setError((json as { message: string }).message);
        return;
      }
      const updated = json as BookingDetailData;
      setBooking(updated);
      setDraft(toDraftForm(updated));
    });

  const submitBooking = () =>
    run(async () => {
      const result = await callAction(`/api/bookings/${booking.id}/submit`);
      if (!result.ok) setError(result.message);
      else setBooking(result.data);
    });

  const cancelBooking = () =>
    run(async () => {
      const reason = window.prompt("Reason for cancelling (optional):") ?? undefined;
      const result = await callAction(`/api/bookings/${booking.id}/cancel`, { reason });
      if (!result.ok) setError(result.message);
      else setBooking(result.data);
    });

  const rescheduleBooking = () =>
    run(async () => {
      const result = await callAction(`/api/bookings/${booking.id}/reschedule`, {
        new_date: rescheduleDate,
        new_time: rescheduleTime ? `${rescheduleTime}:00` : null,
      });
      if (!result.ok) setError(result.message);
      else setBooking(result.data);
    });

  const startReview = () =>
    run(async () => {
      const result = await callAction(`/api/artist/bookings/${booking.id}/review`);
      if (!result.ok) setError(result.message);
      else setBooking(result.data);
    });

  const sendQuote = () =>
    run(async () => {
      const result = await callAction(`/api/artist/bookings/${booking.id}/quotes`, {
        amount: Number(quoteAmount),
        currency: booking.currency,
        terms: quoteTerms || null,
      });
      if (!result.ok) setError(result.message);
      else {
        setBooking(result.data);
        setQuoteAmount("");
        setQuoteTerms("");
      }
    });

  const acceptQuote = (quoteId: string) =>
    run(async () => {
      const result = await callAction(`/api/bookings/${booking.id}/quotes/${quoteId}/accept`);
      if (!result.ok) setError(result.message);
      else setBooking(result.data);
    });

  const rejectQuote = (quoteId: string) =>
    run(async () => {
      const reason = window.prompt("Reason for declining (optional):") ?? undefined;
      const result = await callAction(`/api/bookings/${booking.id}/quotes/${quoteId}/reject`, {
        reason,
      });
      if (!result.ok) setError(result.message);
      else setBooking(result.data);
    });

  const uploadImage = (file: File) =>
    run(async () => {
      const formData = new FormData();
      formData.set("file", file);
      const response = await fetch(`/api/bookings/${booking.id}/attachments`, {
        method: "POST",
        body: formData,
      });
      const json = (await response.json()) as { message: string } | unknown;
      if (!response.ok) {
        setError((json as { message: string }).message);
        return;
      }
      const detailResponse = await fetch(`/api/bookings/${booking.id}`);
      if (detailResponse.ok) setBooking((await detailResponse.json()) as BookingDetailData);
    });

  const isDraft = booking.status === "draft";
  const pendingQuote = booking.quotes.find((q) => q.status === "pending");

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            {viewerIsCustomer
              ? (booking.artist_display_name ?? "Booking")
              : (booking.customer_display_name ?? "Booking")}
          </h1>
          {booking.service_name ? (
            <p className="mt-1 text-text-secondary">{booking.service_name}</p>
          ) : null}
        </div>
        <span className="rounded-full border border-border px-3 py-1 text-sm font-medium text-text-primary">
          {BOOKING_STATUS_LABELS[booking.status]}
        </span>
      </div>

      {error ? (
        <p className="mt-4 rounded-md bg-danger-surface px-3 py-2 text-sm text-danger">{error}</p>
      ) : null}

      {isDraft && viewerIsCustomer ? (
        <section className="mt-6 rounded-xl border border-border bg-surface p-4">
          <h2 className="font-medium text-text-primary">Request details</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="flex flex-col text-sm text-text-secondary">
              Service
              <select
                value={draft.service_id}
                onChange={(e) => setDraft({ ...draft, service_id: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              >
                <option value="">Select a service</option>
                {bookableServices.map((service) => (
                  <option key={service.id} value={service.id}>
                    {service.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Event type
              <select
                value={draft.event_type}
                onChange={(e) => setDraft({ ...draft, event_type: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              >
                <option value="">Select an event type</option>
                {(Object.keys(EVENT_TYPE_LABELS) as EventType[]).map((value) => (
                  <option key={value} value={value}>
                    {EVENT_TYPE_LABELS[value]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Date
              <input
                type="date"
                value={draft.requested_date}
                onChange={(e) => setDraft({ ...draft, requested_date: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Time (optional)
              <input
                type="time"
                value={draft.requested_time}
                onChange={(e) => setDraft({ ...draft, requested_time: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Location
              <select
                value={draft.location_type}
                onChange={(e) => setDraft({ ...draft, location_type: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              >
                <option value="">Select a location type</option>
                <option value="artist_studio">Artist&apos;s studio</option>
                <option value="customer_location">My location</option>
                <option value="other">Other</option>
              </select>
            </label>
            {(draft.location_type as LocationType) !== "artist_studio" && draft.location_type ? (
              <label className="flex flex-col text-sm text-text-secondary">
                Address
                <input
                  type="text"
                  value={draft.location_address}
                  onChange={(e) => setDraft({ ...draft, location_address: e.target.value })}
                  className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
                />
              </label>
            ) : null}
            <label className="flex flex-col text-sm text-text-secondary">
              Number of customers
              <input
                type="number"
                min={1}
                value={draft.num_customers}
                onChange={(e) => setDraft({ ...draft, num_customers: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Budget min
              <input
                type="number"
                min={0}
                value={draft.budget_min}
                onChange={(e) => setDraft({ ...draft, budget_min: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Budget max
              <input
                type="number"
                min={0}
                value={draft.budget_max}
                onChange={(e) => setDraft({ ...draft, budget_max: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Contact name
              <input
                type="text"
                value={draft.contact_name}
                onChange={(e) => setDraft({ ...draft, contact_name: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Contact email
              <input
                type="email"
                value={draft.contact_email}
                onChange={(e) => setDraft({ ...draft, contact_email: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Contact phone
              <input
                type="tel"
                value={draft.contact_phone}
                onChange={(e) => setDraft({ ...draft, contact_phone: e.target.value })}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
          </div>
          <label className="mt-3 flex flex-col text-sm text-text-secondary">
            Design preferences
            <textarea
              value={draft.design_preferences}
              onChange={(e) => setDraft({ ...draft, design_preferences: e.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              rows={2}
            />
          </label>
          <label className="mt-3 flex flex-col text-sm text-text-secondary">
            Notes
            <textarea
              value={draft.notes}
              onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
              className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              rows={2}
            />
          </label>

          <label className="mt-3 flex flex-col text-sm text-text-secondary">
            Inspiration images
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void uploadImage(file);
              }}
              className="mt-1 text-text-primary"
            />
          </label>

          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => void saveDraft()}
              disabled={isBusy}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
            >
              Save draft
            </button>
            <button
              type="button"
              onClick={() => void submitBooking()}
              disabled={isBusy}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-on-primary disabled:opacity-50"
            >
              Submit request
            </button>
          </div>
        </section>
      ) : (
        <section className="mt-6 rounded-xl border border-border bg-surface p-4">
          <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-text-secondary">Date</dt>
              <dd className="text-text-primary">{booking.requested_date ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Time</dt>
              <dd className="text-text-primary">
                {booking.requested_time ? booking.requested_time.slice(0, 5) : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-text-secondary">Location</dt>
              <dd className="text-text-primary">
                {booking.location_type ?? "—"}
                {booking.location_address ? ` · ${booking.location_address}` : ""}
              </dd>
            </div>
            <div>
              <dt className="text-text-secondary">Number of customers</dt>
              <dd className="text-text-primary">{booking.num_customers ?? "—"}</dd>
            </div>
            {booking.total_amount !== null ? (
              <div>
                <dt className="text-text-secondary">Total</dt>
                <dd className="text-text-primary">
                  {booking.currency} {booking.total_amount}
                </dd>
              </div>
            ) : null}
            {booking.deposit_amount !== null ? (
              <div>
                <dt className="text-text-secondary">Deposit</dt>
                <dd className="text-text-primary">
                  {booking.currency} {booking.deposit_amount}
                </dd>
              </div>
            ) : null}
          </dl>
          {booking.notes ? <p className="mt-3 text-sm text-text-primary">{booking.notes}</p> : null}
          {booking.attachments.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {booking.attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="relative h-20 w-20 overflow-hidden rounded-md border border-border"
                >
                  <Image src={attachment.file_url} alt="" fill className="object-cover" />
                </div>
              ))}
            </div>
          ) : null}
        </section>
      )}

      {!viewerIsCustomer && booking.status === "requested" ? (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => void startReview()}
            disabled={isBusy}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
          >
            Start reviewing
          </button>
        </div>
      ) : null}

      {!viewerIsCustomer && QUOTABLE_STATUSES.has(booking.status) ? (
        <section className="mt-6 rounded-xl border border-border bg-surface p-4">
          <h2 className="font-medium text-text-primary">
            {pendingQuote ? "Send a revised quote" : "Send a quote"}
          </h2>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="flex flex-col text-sm text-text-secondary">
              Amount ({booking.currency})
              <input
                type="number"
                min={0}
                value={quoteAmount}
                onChange={(e) => setQuoteAmount(e.target.value)}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              Terms (optional)
              <input
                type="text"
                value={quoteTerms}
                onChange={(e) => setQuoteTerms(e.target.value)}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <button
              type="button"
              onClick={() => void sendQuote()}
              disabled={isBusy || !quoteAmount}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-on-primary disabled:opacity-50"
            >
              {pendingQuote ? "Revise quote" : "Send quote"}
            </button>
          </div>
        </section>
      ) : null}

      {booking.quotes.length > 0 ? (
        <section className="mt-6">
          <h2 className="font-medium text-text-primary">Quotes</h2>
          <ul className="mt-3 flex flex-col gap-2">
            {booking.quotes.map((quote) => (
              <li
                key={quote.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface p-3 text-sm"
              >
                <div>
                  <p className="text-text-primary">
                    {quote.currency} {quote.amount} — {quote.status}
                  </p>
                  {quote.terms ? <p className="text-text-secondary">{quote.terms}</p> : null}
                </div>
                {viewerIsCustomer && quote.status === "pending" ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => void acceptQuote(quote.id)}
                      disabled={isBusy}
                      className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-on-primary disabled:opacity-50"
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      onClick={() => void rejectQuote(quote.id)}
                      disabled={isBusy}
                      className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-primary disabled:opacity-50"
                    >
                      Decline
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {RESCHEDULABLE_STATUSES.has(booking.status) ? (
        <section className="mt-6 rounded-xl border border-border bg-surface p-4">
          <h2 className="font-medium text-text-primary">Reschedule</h2>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="flex flex-col text-sm text-text-secondary">
              New date
              <input
                type="date"
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-col text-sm text-text-secondary">
              New time (optional)
              <input
                type="time"
                value={rescheduleTime}
                onChange={(e) => setRescheduleTime(e.target.value)}
                className="mt-1 rounded-md border border-border px-3 py-2 text-text-primary"
              />
            </label>
            <button
              type="button"
              onClick={() => void rescheduleBooking()}
              disabled={isBusy || !rescheduleDate}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
            >
              Request reschedule
            </button>
          </div>
        </section>
      ) : null}

      {CANCELLABLE_STATUSES.has(booking.status) ? (
        <div className="mt-6">
          <button
            type="button"
            onClick={() => void cancelBooking()}
            disabled={isBusy}
            className="rounded-md border border-danger px-4 py-2 text-sm font-medium text-danger hover:bg-danger-surface disabled:opacity-50"
          >
            Cancel booking
          </button>
        </div>
      ) : null}

      <BookingPayments bookingId={booking.id} bookingStatus={booking.status} />

      {viewerIsCustomer && booking.status === "completed" ? (
        <BookingReviewForm bookingId={booking.id} />
      ) : null}

      <BookingConversation bookingId={booking.id} />

      <section className="mt-8">
        <h2 className="font-medium text-text-primary">History</h2>
        <ul className="mt-3 flex flex-col gap-2 text-sm text-text-secondary">
          {booking.status_history.map((entry) => (
            <li key={entry.id} className="rounded-lg border border-border bg-surface p-3">
              <p className="text-text-primary">
                {entry.from_status
                  ? `${BOOKING_STATUS_LABELS[entry.from_status]} → ${BOOKING_STATUS_LABELS[entry.to_status]}`
                  : `Created as ${BOOKING_STATUS_LABELS[entry.to_status]}`}
              </p>
              {entry.reason ? <p>{entry.reason}</p> : null}
              <p className="text-xs">{new Date(entry.created_at).toLocaleString()}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

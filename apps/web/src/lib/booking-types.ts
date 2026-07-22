/** Shapes returned by the backend's booking endpoints (see
 * app/schemas/booking.py) — see docs/booking-lifecycle.md. */

export type BookingStatus =
  | "draft"
  | "requested"
  | "artist_reviewing"
  | "quotation_sent"
  | "customer_reviewing"
  | "confirmed"
  | "deposit_pending"
  | "deposit_paid"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "rejected"
  | "refund_requested"
  | "refunded"
  | "disputed";

export const BOOKING_STATUS_LABELS: Record<BookingStatus, string> = {
  draft: "Draft",
  requested: "Requested",
  artist_reviewing: "Artist reviewing",
  quotation_sent: "Quote sent",
  customer_reviewing: "Reviewing quote",
  confirmed: "Confirmed",
  deposit_pending: "Deposit pending",
  deposit_paid: "Deposit paid",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
  rejected: "Rejected",
  refund_requested: "Refund requested",
  refunded: "Refunded",
  disputed: "Disputed",
};

export type EventType =
  | "wedding"
  | "engagement"
  | "festival"
  | "baby_shower"
  | "party"
  | "corporate_event"
  | "other";

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  wedding: "Wedding",
  engagement: "Engagement",
  festival: "Festival",
  baby_shower: "Baby shower",
  party: "Party",
  corporate_event: "Corporate event",
  other: "Other",
};

export type LocationType = "customer_location" | "artist_studio" | "other";

export interface BookingQuoteData {
  id: string;
  amount: number;
  currency: string;
  terms: string | null;
  valid_until: string | null;
  status: "pending" | "accepted" | "declined" | "expired" | "superseded";
  created_at: string;
}

export interface BookingStatusHistoryData {
  id: string;
  from_status: BookingStatus | null;
  to_status: BookingStatus;
  changed_by: string | null;
  reason: string | null;
  created_at: string;
}

export interface BookingAttachmentData {
  id: string;
  file_url: string;
  file_type: string;
  caption: string | null;
  uploaded_by: string;
  created_at: string;
}

export interface BookingSummaryData {
  id: string;
  artist_profile_id: string;
  artist_display_name: string | null;
  customer_id: string;
  customer_display_name: string | null;
  service_id: string | null;
  service_name: string | null;
  status: BookingStatus;
  requested_date: string | null;
  requested_time: string | null;
  location_type: LocationType | null;
  event_type: EventType | null;
  num_customers: number | null;
  total_amount: number | null;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface BookingDetailData extends BookingSummaryData {
  design_id: string | null;
  location_address: string | null;
  design_preferences: string | null;
  notes: string | null;
  budget_min: number | null;
  budget_max: number | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  deposit_amount: number | null;
  cancelled_by: string | null;
  cancellation_reason: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  quotes: BookingQuoteData[];
  status_history: BookingStatusHistoryData[];
  attachments: BookingAttachmentData[];
}

/** Shapes returned by the backend's booking-messaging endpoints (see
 * app/schemas/messaging.py) — see docs/booking-messaging.md. */

export interface MessageData {
  id: string;
  conversation_id: string;
  sender_id: string;
  body: string | null;
  attachment_url: string | null;
  message_type: "text" | "image" | "system";
  is_read: boolean;
  created_at: string;
}

export interface MessagePageData {
  items: MessageData[];
  page_info: { next_cursor: string | null; has_more: boolean };
}

export interface ConversationBookingContextData {
  booking_id: string;
  status: string;
  requested_date: string | null;
  service_name: string | null;
  artist_profile_id: string;
}

export interface ConversationSummaryData {
  id: string;
  booking: ConversationBookingContextData;
  other_party_display_name: string | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  unread_count: number;
}

export interface ConversationDetailData {
  id: string;
  booking: ConversationBookingContextData;
  other_party_display_name: string | null;
  my_last_read_at: string | null;
}

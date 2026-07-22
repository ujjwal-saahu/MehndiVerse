/** Shapes returned by the backend's notification endpoints (see
 * app/schemas/notification.py) — see docs/booking-messaging.md. */

export interface NotificationData {
  id: string;
  type: string;
  channel: "in_app" | "push" | "email" | "sms";
  title: string;
  body: string;
  data: Record<string, unknown> | null;
  is_read: boolean;
  read_at: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface NotificationListData {
  items: NotificationData[];
  page_info: { next_cursor: string | null; has_more: boolean };
  unread_count: number;
}

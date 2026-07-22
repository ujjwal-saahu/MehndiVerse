/** Shapes returned by the backend's community-and-trust endpoints (see
 * app/schemas/comment.py, app/schemas/review.py, app/schemas/moderation.py,
 * and docs/community-and-trust.md). */

export interface ReplyData {
  id: string;
  design_id: string;
  user_id: string;
  user_display_name: string | null;
  parent_comment_id: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface CommentData {
  id: string;
  design_id: string;
  user_id: string;
  user_display_name: string | null;
  parent_comment_id: null;
  body: string;
  replies: ReplyData[];
  created_at: string;
  updated_at: string;
}

export interface CommentListData {
  items: CommentData[];
}

export interface ReviewData {
  id: string;
  booking_id: string;
  customer_id: string;
  customer_display_name: string | null;
  artist_profile_id: string;
  rating: number;
  body: string | null;
  created_at: string;
}

export interface ReviewListData {
  items: ReviewData[];
  rating_average: number;
  rating_count: number;
}

export interface ReportData {
  id: string;
  reporter_id: string;
  reported_entity_type: string;
  reported_entity_id: string;
  status: string;
  reason: string;
  resolution_notes: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface ReportQueueItemData extends ReportData {
  entity_snapshot: Record<string, unknown> | null;
}

export interface ReportQueueData {
  items: ReportQueueItemData[];
  page_info: { next_cursor: string | null; has_more: boolean };
}

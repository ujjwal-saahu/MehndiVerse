/** Shapes returned by the backend's admin-dashboard endpoints — see
 * app/schemas/admin.py and docs/admin-dashboard.md. */

export interface AdminPageInfo {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface DashboardOverviewData {
  pending_artist_verifications: number;
  pending_reports: number;
  pending_refunds: number;
  disputed_bookings: number;
  total_users: number;
  total_artists: number;
  total_designs: number;
  total_bookings: number;
}

export interface AdminUserData {
  id: string;
  email: string;
  role: string;
  status: string;
  display_name: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface ArtistVerificationQueueItemData {
  id: string;
  user_id: string;
  professional_name: string | null;
  business_name: string | null;
  verification_status: string;
  submitted_at: string | null;
  document_count: number;
}

export interface ArtistProfileData {
  id: string;
  user_id: string;
  professional_name: string | null;
  business_name: string | null;
  headline: string | null;
  bio: string | null;
  years_experience: number | null;
  country: string | null;
  city: string | null;
  service_areas: string[];
  languages: string[];
  contact_email: string | null;
  contact_phone: string | null;
  social_links: Record<string, string>;
  profile_image_url: string | null;
  cover_image_url: string | null;
  verification_status: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  more_info_request: string | null;
  is_editable: boolean;
  missing_requirements: string[];
  created_at: string;
  updated_at: string;
}

export interface ArtistDocumentData {
  id: string;
  document_type: string;
  original_filename: string | null;
  content_type: string;
  file_size_bytes: number;
  status: string;
  rejection_reason: string | null;
  reviewed_at: string | null;
  view_url: string;
  created_at: string;
}

export interface AdminDesignListItemData {
  id: string;
  title: string;
  status: string;
  artist_profile_id: string | null;
  artist_display_name: string | null;
  is_featured: boolean;
  view_count: number;
  like_count: number;
  created_at: string;
}

export interface CategoryData {
  id: string;
  name: string;
  slug: string;
  category_type: string;
  description: string | null;
  parent_category_id: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface TagData {
  id: string;
  name: string;
  slug: string;
}

export interface AdminBookingListItemData {
  id: string;
  customer_id: string;
  customer_display_name: string | null;
  artist_profile_id: string;
  artist_display_name: string | null;
  status: string;
  requested_date: string | null;
  total_amount: number | null;
  currency: string;
  created_at: string;
}

export interface AdminPaymentListItemData {
  id: string;
  booking_id: string;
  payer_id: string;
  amount: number;
  currency: string;
  status: string;
  payment_type: string;
  provider: string;
  created_at: string;
}

export interface AdminRefundListItemData {
  id: string;
  payment_id: string;
  amount: number;
  currency: string;
  reason: string | null;
  status: string;
  requested_at: string;
  processed_at: string | null;
}

export interface ReportQueueItemData {
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
  entity_snapshot: Record<string, unknown> | null;
}

export interface AdminReviewListItemData {
  id: string;
  booking_id: string;
  customer_id: string;
  customer_display_name: string | null;
  artist_profile_id: string;
  rating: number;
  body: string | null;
  is_flagged: boolean;
  is_deleted: boolean;
  created_at: string;
}

export interface PromoBannerData {
  id: string;
  title: string;
  subtitle: string | null;
  image_url: string;
  link_url: string | null;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface FeaturedCollectionItemData {
  id: string;
  design_id: string;
  sort_order: number;
}

export interface FeaturedCollectionData {
  id: string;
  title: string;
  description: string | null;
  cover_image_url: string | null;
  is_active: boolean;
  sort_order: number;
  items: FeaturedCollectionItemData[];
  created_at: string;
  updated_at: string;
}

export interface NotificationCampaignData {
  id: string;
  title: string;
  body: string;
  target_role: string | null;
  status: string;
  recipient_count: number | null;
  sent_at: string | null;
  created_at: string;
}

export interface GlobalAuditLogEntryData {
  id: string;
  actor_id: string | null;
  actor_display_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  created_at: string;
}

export interface SystemSettingData {
  id: string;
  key: string;
  value: unknown;
  description: string | null;
  is_public: boolean;
  updated_by: string | null;
  updated_at: string;
}

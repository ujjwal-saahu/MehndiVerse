/** Shapes returned by the backend's artist onboarding/verification endpoints
 * (see app/schemas/artist.py) — shared across the onboarding wizard,
 * verification-status screen, and admin review pages. */

import type { PageInfo } from "./gallery-types";

export type ArtistVerificationStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "more_information_required"
  | "approved"
  | "rejected"
  | "suspended";

export const SOCIAL_PLATFORMS = [
  "instagram",
  "facebook",
  "twitter",
  "tiktok",
  "youtube",
  "pinterest",
  "website",
] as const;

export type SocialPlatform = (typeof SOCIAL_PLATFORMS)[number];

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
  social_links: Partial<Record<SocialPlatform, string>>;
  profile_image_url: string | null;
  cover_image_url: string | null;
  verification_status: ArtistVerificationStatus;
  submitted_at: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  more_info_request: string | null;
  is_editable: boolean;
  missing_requirements: string[];
  created_at: string;
  updated_at: string;
}

export type DocumentType = "id_proof" | "address_proof" | "business_license" | "portfolio_sample";

export type DocumentStatus = "pending" | "approved" | "rejected";

export interface ArtistDocumentData {
  id: string;
  document_type: DocumentType;
  original_filename: string | null;
  content_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  rejection_reason: string | null;
  reviewed_at: string | null;
  view_url: string;
  created_at: string;
}

export interface AuditLogEntryData {
  id: string;
  actor_id: string | null;
  actor_display_name: string | null;
  action: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListData {
  items: AuditLogEntryData[];
  page_info: PageInfo;
}

export interface ArtistVerificationQueueItemData {
  id: string;
  user_id: string;
  professional_name: string | null;
  business_name: string | null;
  verification_status: ArtistVerificationStatus;
  submitted_at: string | null;
  document_count: number;
}

export interface ArtistVerificationQueueData {
  items: ArtistVerificationQueueItemData[];
  page_info: PageInfo;
}

export const MISSING_REQUIREMENT_LABELS: Record<string, string> = {
  professional_name: "Professional name",
  bio: "Biography",
  years_experience: "Years of experience",
  country: "Country",
  city: "City",
  identity_document: "Identity document",
};

export const VERIFICATION_STATUS_LABELS: Record<ArtistVerificationStatus, string> = {
  draft: "Draft",
  submitted: "Submitted — awaiting review",
  under_review: "Under review",
  more_information_required: "More information needed",
  approved: "Approved",
  rejected: "Rejected",
  suspended: "Suspended",
};

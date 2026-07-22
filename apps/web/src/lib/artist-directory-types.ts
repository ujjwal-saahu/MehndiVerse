/** Shapes returned by the backend's public artist directory/profile and
 * self-service services/analytics endpoints (see
 * app/schemas/artist_directory.py) — see docs/artist-directory.md. */

import type { DesignSummaryData, PageInfo } from "./gallery-types";

export type PricingType = "fixed" | "range" | "custom_quote";

export interface ArtistServiceData {
  id: string;
  name: string;
  description: string | null;
  pricing_type: PricingType;
  price_amount: number | null;
  price_min: number | null;
  price_max: number | null;
  currency: string;
  duration_minutes: number | null;
  customer_capacity: number | null;
  deposit_required: boolean;
  deposit_amount: number | null;
  travel_charge_amount: number | null;
  cancellation_policy: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ArtistAvailabilitySlotData {
  day_of_week: number;
  start_time: string;
  end_time: string;
}

export interface ArtistPublicProfileData {
  id: string;
  user_id: string;
  display_name: string;
  professional_name: string | null;
  business_name: string | null;
  headline: string | null;
  bio: string | null;
  years_experience: number | null;
  city: string | null;
  country: string | null;
  service_areas: string[];
  languages: string[];
  profile_image_url: string | null;
  cover_image_url: string | null;
  social_links: Record<string, string>;
  is_verified: boolean;
  rating_average: number;
  rating_count: number;
  follower_count: number;
  is_followed: boolean;
  is_accepting_bookings: boolean;
  services: ArtistServiceData[];
  availability_preview: ArtistAvailabilitySlotData[];
  portfolio_preview: DesignSummaryData[];
  portfolio_count: number;
}

export interface ArtistDirectoryItemData {
  id: string;
  display_name: string;
  headline: string | null;
  avatar_url: string | null;
  city: string | null;
  country: string | null;
  years_experience: number | null;
  is_verified: boolean;
  rating_average: number;
  rating_count: number;
  is_accepting_bookings: boolean;
}

export interface ArtistDirectoryListData {
  items: ArtistDirectoryItemData[];
  page_info: PageInfo;
}

export interface PortfolioAnalyticsData {
  total_designs: number;
  published_designs: number;
  total_views: number;
  total_likes: number;
  total_saves: number;
  top_designs: DesignSummaryData[];
}

export const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

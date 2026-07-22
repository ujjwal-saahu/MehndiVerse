/** Shapes returned by the backend's public design-gallery endpoints (see
 * app/schemas/design.py) — shared across the gallery pages/components. */

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

export interface ArtistSummaryData {
  id: string;
  display_name: string;
  avatar_url: string | null;
  headline: string | null;
  rating_average: number;
  rating_count: number;
  is_accepting_bookings: boolean;
}

export interface DesignSummaryData {
  id: string;
  artist_profile_id: string | null;
  artist_display_name: string | null;
  title: string;
  status: string;
  is_featured: boolean;
  is_premium: boolean;
  difficulty_level: string | null;
  body_placement: string | null;
  thumbnail_url: string | null;
  view_count: number;
  like_count: number;
  save_count: number;
  created_at: string;
}

export interface DesignImageData {
  id: string;
  design_id: string;
  status: string;
  image_url: string | null;
  thumbnail_small_url: string | null;
  thumbnail_medium_url: string | null;
  width: number | null;
  height: number | null;
  sort_order: number;
  is_primary: boolean;
  processing_error: string | null;
}

export interface DesignDetailData {
  id: string;
  artist_profile_id: string | null;
  artist: ArtistSummaryData | null;
  title: string;
  description: string | null;
  difficulty_level: string | null;
  body_placement: string | null;
  status: string;
  is_featured: boolean;
  is_premium: boolean;
  // True when this is a premium design and the viewer lacks premium access
  // — see docs/subscriptions-and-entitlements.md#premium-design-access.
  // `images[].image_url`/`thumbnail_medium_url` are withheld when true.
  premium_locked: boolean;
  view_count: number;
  like_count: number;
  save_count: number;
  is_liked: boolean;
  is_saved: boolean;
  categories: CategoryData[];
  tags: string[];
  images: DesignImageData[];
  created_at: string;
  updated_at: string;
}

export interface PageInfo {
  next_cursor: string | null;
  has_more: boolean;
}

export interface DesignListData {
  items: DesignSummaryData[];
  page_info: PageInfo;
}

export interface HomeFeedData {
  latest: DesignSummaryData[];
  featured: DesignSummaryData[];
  trending: DesignSummaryData[];
}

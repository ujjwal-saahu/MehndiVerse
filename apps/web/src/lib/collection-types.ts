/** Shapes returned by the backend's collections endpoints (see
 * app/schemas/engagement.py) — shared across the collections pages/components. */

import type { DesignSummaryData, PageInfo } from "./gallery-types";

export interface CollectionData {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  is_private: boolean;
  is_owner: boolean;
  cover_image_url: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface CollectionListData {
  items: CollectionData[];
  page_info: PageInfo;
}

export interface CollectionItemsData {
  items: DesignSummaryData[];
  page_info: PageInfo;
}

export interface LikeStatusData {
  liked: boolean;
  like_count: number;
}

export interface SaveStatusData {
  saved: boolean;
  save_count: number;
}

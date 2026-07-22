/** Shapes returned by the backend's hand/foot preview endpoints (see
 * app/schemas/preview.py) — see docs/hand-foot-preview.md. Every image URL
 * here is a short-lived signed URL minted fresh on every read — never
 * cache one across page loads. */

export interface OverlayTransform {
  x: number;
  y: number;
  scale: number;
  rotation_degrees: number;
  flip_horizontal: boolean;
  opacity: number;
}

export const DEFAULT_OVERLAY_TRANSFORM: OverlayTransform = {
  x: 0.5,
  y: 0.5,
  scale: 1,
  rotation_degrees: 0,
  flip_horizontal: false,
  opacity: 1,
};

export interface PreviewDesignSummary {
  id: string;
  title: string;
  thumbnail_url: string | null;
  is_premium: boolean;
}

export interface PreviewProjectData {
  id: string;
  design: PreviewDesignSummary | null;
  source_image_url: string;
  result_image_url: string | null;
  overlay_transform: OverlayTransform | null;
  source_width: number | null;
  source_height: number | null;
  status: string;
  error_message: string | null;
  shared_with_booking_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExportPreviewResponse {
  result_image_url: string;
}

export interface SharePreviewResponse {
  url: string;
  expires_in_seconds: number;
}

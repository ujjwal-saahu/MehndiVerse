"use client";

/** Local (never-uploaded-unless-saved) image helpers for the hand/foot
 * preview editor — see docs/hand-foot-preview.md#memory-and-performance-
 * safeguards. Downscaling happens the moment a photo is picked, before
 * it's ever held in editor state or drawn to a canvas, so a 12MP phone
 * photo never sits in memory at full resolution during editing. */

export const MAX_EDIT_DIMENSION = 1600;
export const MAX_PREVIEW_PHOTO_BYTES = 15 * 1024 * 1024;
export const ALLOWED_PREVIEW_PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** `crossOrigin` must be set for any image that isn't a same-origin/blob:
 * URL — the source photo (once reloaded from a signed URL) and every
 * design overlay image are both served from Supabase Storage, a different
 * origin than this app, so compositing them onto a canvas and reading the
 * result back out (`toBlob`) requires the storage bucket to serve
 * permissive CORS headers. See docs/hand-foot-preview.md#cors-dependency. */
export function loadImage(
  src: string,
  { crossOrigin = false }: { crossOrigin?: boolean } = {},
): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    if (crossOrigin) image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Could not load the image."));
    image.src = src;
  });
}

/** Re-encodes `file` to fit within `maxDimension` x `maxDimension`,
 * preserving aspect ratio — a no-op (same bytes back) if it's already
 * smaller. Runs entirely on-device via an offscreen canvas; nothing is
 * uploaded to produce this. */
export async function downscaleImageFile(
  file: File,
  maxDimension: number = MAX_EDIT_DIMENSION,
): Promise<Blob> {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await loadImage(objectUrl);
    if (image.naturalWidth <= maxDimension && image.naturalHeight <= maxDimension) {
      return file;
    }
    const scale = maxDimension / Math.max(image.naturalWidth, image.naturalHeight);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.9),
    );
    return blob ?? file;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export function validatePreviewPhoto(file: File): string | null {
  if (!ALLOWED_PREVIEW_PHOTO_TYPES.includes(file.type)) {
    return "Please choose a JPEG, PNG, or WEBP photo.";
  }
  if (file.size > MAX_PREVIEW_PHOTO_BYTES) {
    return "That photo is too large (max 15 MB).";
  }
  return null;
}

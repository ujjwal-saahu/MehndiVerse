"use client";

import Image from "next/image";
import { useRef, useState } from "react";

import type { DesignImageData } from "@/lib/gallery-types";

/** Main image + thumbnail strip, with a full-screen zoom on click — see
 * docs/design-gallery.md#image-gallery-and-zoom. Only `ready` images are
 * ever shown (matches the backend's own public-visibility filtering: a
 * `pending`/`processing`/`failed` image never has a usable URL anyway). */
export function ImageGallery({ images, title }: { images: DesignImageData[]; title: string }) {
  const readyImages = images.filter((image) => image.status === "ready" && image.image_url);
  const [activeIndex, setActiveIndex] = useState(0);
  const dialogRef = useRef<HTMLDialogElement>(null);

  if (readyImages.length === 0) {
    return (
      <div
        role="img"
        aria-label={`${title} mehndi design — image not yet available`}
        className="flex aspect-square w-full items-center justify-center rounded-xl bg-surface-variant text-text-secondary"
      >
        Image coming soon
      </div>
    );
  }

  // `readyImages.length > 0` was already checked above, so index 0 always
  // exists; guards against `activeIndex` ever landing out of range.
  const active = readyImages[activeIndex] ?? readyImages[0]!;

  return (
    <div>
      <button
        type="button"
        onClick={() => dialogRef.current?.showModal()}
        aria-label={`Zoom in on ${title} mehndi design, image ${activeIndex + 1} of ${readyImages.length}`}
        className="block w-full overflow-hidden rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
      >
        <div className="relative aspect-square w-full bg-surface-variant">
          <Image
            src={active.thumbnail_medium_url ?? active.image_url ?? ""}
            alt={`${title} mehndi design, image ${activeIndex + 1} of ${readyImages.length}`}
            fill
            sizes="(min-width: 1024px) 50vw, 100vw"
            className="object-cover"
            priority
          />
        </div>
      </button>

      {readyImages.length > 1 ? (
        <div className="mt-3 flex gap-2 overflow-x-auto" role="list" aria-label="More images">
          {readyImages.map((image, index) => (
            <button
              key={image.id}
              type="button"
              role="listitem"
              onClick={() => setActiveIndex(index)}
              aria-current={index === activeIndex}
              aria-label={`Show image ${index + 1} of ${readyImages.length}`}
              className={`relative h-16 w-16 shrink-0 overflow-hidden rounded-md border-2 ${
                index === activeIndex ? "border-primary" : "border-transparent"
              }`}
            >
              <Image
                src={image.thumbnail_small_url ?? image.image_url ?? ""}
                alt=""
                fill
                sizes="64px"
                className="object-cover"
              />
            </button>
          ))}
        </div>
      ) : null}

      <dialog
        ref={dialogRef}
        aria-label={`${title} mehndi design, enlarged`}
        className="max-h-[90vh] max-w-[90vw] rounded-lg bg-background p-0 backdrop:bg-black/80"
        onClick={(event) => {
          if (event.target === dialogRef.current) dialogRef.current?.close();
        }}
      >
        <div className="relative h-[85vh] w-[85vw]">
          <button
            type="button"
            onClick={() => dialogRef.current?.close()}
            aria-label="Close zoomed image"
            className="absolute right-2 top-2 z-10 rounded-full bg-black/60 p-2 text-white"
          >
            ✕
          </button>
          <Image
            src={active.image_url ?? active.thumbnail_medium_url ?? ""}
            alt={`${title} mehndi design, zoomed in, image ${activeIndex + 1} of ${readyImages.length}`}
            fill
            sizes="85vw"
            className="object-contain"
          />
        </div>
      </dialog>
    </div>
  );
}

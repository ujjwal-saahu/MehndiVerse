"use client";

import { forwardRef, useImperativeHandle, useRef, useState } from "react";

import { clamp, loadImage } from "@/lib/image-utils";
import type { OverlayTransform } from "@/lib/preview-types";

/** The overlay's width at `scale: 1`, as a fraction of the photo's width —
 * a sensible default sticker size a user then adjusts. Used identically
 * here (CSS) and in `exportComposite` (canvas) so the two never disagree. */
export const BASE_OVERLAY_WIDTH_FRACTION = 0.4;

export interface OverlayEditorHandle {
  /** Renders photo + overlay, at the photo's natural resolution, onto an
   * off-screen canvas and returns the flattened result — this IS "export":
   * compositing happens entirely on-device, nothing is rasterized by the
   * backend. See docs/hand-foot-preview.md#export. */
  exportComposite: () => Promise<Blob>;
}

interface DragState {
  mode: "move" | "transform";
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startTransform: OverlayTransform;
  centerClientX: number;
  centerClientY: number;
  startAngle: number;
  startDistance: number;
}

interface OverlayEditorProps {
  photoUrl: string;
  designImageUrl: string | null;
  transform: OverlayTransform;
  onTransformChange: (transform: OverlayTransform) => void;
}

export const OverlayEditor = forwardRef<OverlayEditorHandle, OverlayEditorProps>(
  function OverlayEditor({ photoUrl, designImageUrl, transform, onTransformChange }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const dragRef = useRef<DragState | null>(null);
    const [containerAspect, setContainerAspect] = useState(1); // height / width

    useImperativeHandle(ref, () => ({
      exportComposite: async () => {
        const photo = await loadImage(photoUrl, { crossOrigin: true });
        const canvas = document.createElement("canvas");
        canvas.width = photo.naturalWidth;
        canvas.height = photo.naturalHeight;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("Could not prepare the export.");
        ctx.drawImage(photo, 0, 0, canvas.width, canvas.height);

        if (designImageUrl) {
          const overlay = await loadImage(designImageUrl, { crossOrigin: true });
          const overlayWidth = canvas.width * BASE_OVERLAY_WIDTH_FRACTION * transform.scale;
          const overlayHeight = overlayWidth * (overlay.naturalHeight / overlay.naturalWidth);
          ctx.save();
          ctx.globalAlpha = transform.opacity;
          ctx.translate(transform.x * canvas.width, transform.y * canvas.height);
          ctx.rotate((transform.rotation_degrees * Math.PI) / 180);
          ctx.scale(transform.flip_horizontal ? -1 : 1, 1);
          ctx.drawImage(
            overlay,
            -overlayWidth / 2,
            -overlayHeight / 2,
            overlayWidth,
            overlayHeight,
          );
          ctx.restore();
        }

        const blob = await new Promise<Blob | null>((resolve) =>
          canvas.toBlob(resolve, "image/png"),
        );
        if (!blob) throw new Error("Could not prepare the export.");
        return blob;
      },
    }));

    const beginDrag = (event: React.PointerEvent<HTMLDivElement>, mode: "move" | "transform") => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      event.currentTarget.setPointerCapture(event.pointerId);
      const centerClientX = rect.left + transform.x * rect.width;
      const centerClientY = rect.top + transform.y * rect.height;
      dragRef.current = {
        mode,
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startTransform: transform,
        centerClientX,
        centerClientY,
        startAngle: Math.atan2(event.clientY - centerClientY, event.clientX - centerClientX),
        startDistance: Math.hypot(event.clientX - centerClientX, event.clientY - centerClientY),
      };
    };

    const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
      const drag = dragRef.current;
      const rect = containerRef.current?.getBoundingClientRect();
      if (!drag || !rect || drag.pointerId !== event.pointerId) return;

      if (drag.mode === "move") {
        const dxFraction = (event.clientX - drag.startClientX) / rect.width;
        const dyFraction = (event.clientY - drag.startClientY) / rect.height;
        onTransformChange({
          ...transform,
          x: clamp(drag.startTransform.x + dxFraction, 0, 1),
          y: clamp(drag.startTransform.y + dyFraction, 0, 1),
        });
      } else {
        const angleNow = Math.atan2(
          event.clientY - drag.centerClientY,
          event.clientX - drag.centerClientX,
        );
        const distanceNow = Math.hypot(
          event.clientX - drag.centerClientX,
          event.clientY - drag.centerClientY,
        );
        const deltaAngleDeg = ((angleNow - drag.startAngle) * 180) / Math.PI;
        const scaleRatio = drag.startDistance > 0 ? distanceNow / drag.startDistance : 1;
        onTransformChange({
          ...transform,
          rotation_degrees: drag.startTransform.rotation_degrees + deltaAngleDeg,
          scale: clamp(drag.startTransform.scale * scaleRatio, 0.2, 5),
        });
      }
    };

    const endDrag = () => {
      dragRef.current = null;
    };

    const overlayWidthPercent = BASE_OVERLAY_WIDTH_FRACTION * 100 * transform.scale;

    return (
      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-xl bg-black"
        style={{ paddingTop: `${containerAspect * 100}%` }}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- local blob/signed URLs, not a Next-optimizable remote asset */}
        <img
          src={photoUrl}
          alt="Your hand or foot photo"
          className="absolute inset-0 h-full w-full object-contain"
          onLoad={(event) => {
            const img = event.currentTarget;
            if (img.naturalWidth > 0) {
              setContainerAspect(img.naturalHeight / img.naturalWidth);
            }
          }}
          draggable={false}
        />
        {designImageUrl ? (
          <div
            className="absolute cursor-move touch-none select-none"
            style={{
              left: `${transform.x * 100}%`,
              top: `${transform.y * 100}%`,
              width: `${overlayWidthPercent}%`,
              opacity: transform.opacity,
              transform: `translate(-50%, -50%) rotate(${transform.rotation_degrees}deg) scaleX(${
                transform.flip_horizontal ? -1 : 1
              })`,
            }}
            onPointerDown={(event) => beginDrag(event, "move")}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- overlay preview, composited client-side */}
            <img src={designImageUrl} alt="Design overlay" className="w-full" draggable={false} />
            <div
              role="slider"
              aria-label="Resize and rotate the design overlay"
              aria-valuenow={transform.scale}
              tabIndex={0}
              className="absolute -right-3 -bottom-3 h-6 w-6 cursor-nwse-resize rounded-full border-2 border-white bg-primary touch-none"
              onPointerDown={(event) => beginDrag(event, "transform")}
            />
          </div>
        ) : null}
      </div>
    );
  },
);

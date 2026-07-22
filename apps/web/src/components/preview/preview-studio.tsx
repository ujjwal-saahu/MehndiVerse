"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { BookingSummaryData } from "@/lib/booking-types";
import type { DesignSummaryData } from "@/lib/gallery-types";
import { downscaleImageFile, validatePreviewPhoto } from "@/lib/image-utils";
import { DEFAULT_OVERLAY_TRANSFORM } from "@/lib/preview-types";
import type {
  OverlayTransform,
  PreviewProjectData,
  SharePreviewResponse,
} from "@/lib/preview-types";

import { OverlayEditor } from "./overlay-editor";
import type { OverlayEditorHandle } from "./overlay-editor";

type LoadState = { status: "loading" } | { status: "error"; message: string } | { status: "ready" };

async function parseErrorMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  return (body as { message?: string }).message ?? "Something went wrong. Please try again.";
}

export function PreviewStudio({ previewId: initialPreviewId }: { previewId?: string }) {
  const [loadState, setLoadState] = useState<LoadState>(
    initialPreviewId ? { status: "loading" } : { status: "ready" },
  );
  const [previewId, setPreviewId] = useState<string | null>(initialPreviewId ?? null);

  const [photoFile, setPhotoFile] = useState<File | Blob | null>(null);
  const [photoObjectUrl, setPhotoObjectUrl] = useState<string | null>(null);
  const [remotePhotoUrl, setRemotePhotoUrl] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);

  const [selectedDesign, setSelectedDesign] = useState<Pick<
    DesignSummaryData,
    "id" | "title" | "thumbnail_url" | "is_premium"
  > | null>(null);
  const [showDesignPicker, setShowDesignPicker] = useState(false);

  const [transform, setTransform] = useState<OverlayTransform>(DEFAULT_OVERLAY_TRANSFORM);

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isSharing, setIsSharing] = useState(false);
  const [shareResult, setShareResult] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [showSendPicker, setShowSendPicker] = useState(false);
  const [bookings, setBookings] = useState<BookingSummaryData[] | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sendSuccess, setSendSuccess] = useState(false);

  const editorRef = useRef<OverlayEditorHandle>(null);

  useEffect(() => {
    if (!initialPreviewId) return;
    fetch(`/api/previews/${initialPreviewId}`)
      .then((response) =>
        response.ok ? response.json() : Promise.reject(new Error(String(response.status))),
      )
      .then((data: PreviewProjectData) => {
        setRemotePhotoUrl(data.source_image_url);
        setSelectedDesign(data.design);
        setTransform(data.overlay_transform ?? DEFAULT_OVERLAY_TRANSFORM);
        setLoadState({ status: "ready" });
      })
      .catch(() =>
        setLoadState({ status: "error", message: "Could not load this preview project." }),
      );
  }, [initialPreviewId]);

  useEffect(() => {
    return () => {
      if (photoObjectUrl) URL.revokeObjectURL(photoObjectUrl);
    };
  }, [photoObjectUrl]);

  const photoUrl = photoObjectUrl ?? remotePhotoUrl;

  const onPhotoChange = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      setPhotoError(null);
      const validationError = validatePreviewPhoto(file);
      if (validationError) {
        setPhotoError(validationError);
        return;
      }
      const downscaled = await downscaleImageFile(file);
      if (photoObjectUrl) URL.revokeObjectURL(photoObjectUrl);
      setPhotoFile(downscaled);
      setPhotoObjectUrl(URL.createObjectURL(downscaled));
      setRemotePhotoUrl(null);
    },
    [photoObjectUrl],
  );

  const save = async () => {
    if (!photoUrl) {
      setSaveError("Choose a photo first.");
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      const formData = new FormData();
      if (photoFile) formData.set("file", photoFile, "photo.jpg");
      if (selectedDesign) formData.set("design_id", selectedDesign.id);
      formData.set("overlay_transform", JSON.stringify(transform));

      if (previewId) {
        const response = await fetch(`/api/previews/${previewId}`, {
          method: "PATCH",
          body: formData,
        });
        if (!response.ok) throw new Error(await parseErrorMessage(response));
      } else {
        if (!photoFile) {
          setSaveError("Choose a photo first.");
          return;
        }
        const response = await fetch("/api/previews", { method: "POST", body: formData });
        if (!response.ok) throw new Error(await parseErrorMessage(response));
        const created = (await response.json()) as PreviewProjectData;
        setPreviewId(created.id);
        setRemotePhotoUrl(created.source_image_url);
        if (photoObjectUrl) URL.revokeObjectURL(photoObjectUrl);
        setPhotoObjectUrl(null);
        setPhotoFile(null);
      }
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save this preview.");
    } finally {
      setIsSaving(false);
    }
  };

  const exportPreview = async () => {
    if (!editorRef.current) return;
    setIsExporting(true);
    setExportError(null);
    try {
      const blob = await editorRef.current.exportComposite();

      // Always offer a local download — this works even for an unsaved
      // preview, since compositing never required uploading anything.
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = "mehndi-preview.png";
      link.click();
      URL.revokeObjectURL(downloadUrl);

      if (previewId) {
        const formData = new FormData();
        formData.set("file", blob, "export.png");
        const response = await fetch(`/api/previews/${previewId}/export`, {
          method: "POST",
          body: formData,
        });
        if (!response.ok) throw new Error(await parseErrorMessage(response));
      }
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Could not export this preview.");
    } finally {
      setIsExporting(false);
    }
  };

  const share = async () => {
    if (!previewId) {
      setExportError("Save this preview before sharing it.");
      return;
    }
    setIsSharing(true);
    setShareResult(null);
    try {
      const response = await fetch(`/api/previews/${previewId}/share`);
      if (!response.ok) throw new Error(await parseErrorMessage(response));
      const body = (await response.json()) as SharePreviewResponse;
      if (navigator.share) {
        await navigator.share({ title: "My mehndi design preview", url: body.url });
        setShareResult("Shared.");
      } else {
        await navigator.clipboard.writeText(body.url);
        setShareResult("Link copied to clipboard (expires in an hour).");
      }
    } catch (err) {
      setShareResult(err instanceof Error ? err.message : "Could not share this preview.");
    } finally {
      setIsSharing(false);
    }
  };

  const openSendPicker = async () => {
    if (!previewId) {
      setSendError("Save this preview before sending it to an artist.");
      return;
    }
    setShowSendPicker(true);
    if (bookings) return;
    const response = await fetch("/api/bookings/mine");
    if (response.ok) {
      const data = (await response.json()) as BookingSummaryData[];
      setBookings(data.filter((b) => b.status !== "draft"));
    }
  };

  const sendToArtist = async (bookingId: string) => {
    if (!previewId) return;
    setIsSending(true);
    setSendError(null);
    try {
      const response = await fetch(`/api/previews/${previewId}/send-to-artist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ booking_id: bookingId }),
      });
      if (!response.ok) throw new Error(await parseErrorMessage(response));
      setSendSuccess(true);
      setShowSendPicker(false);
    } catch (err) {
      setSendError(err instanceof Error ? err.message : "Could not send this preview.");
    } finally {
      setIsSending(false);
    }
  };

  const remove = async () => {
    if (!previewId) return;
    if (!window.confirm("Delete this preview project? This cannot be undone.")) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      const response = await fetch(`/api/previews/${previewId}`, { method: "DELETE" });
      if (!response.ok && response.status !== 204) {
        throw new Error(await parseErrorMessage(response));
      }
      window.location.href = "/previews";
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Could not delete this preview.");
      setIsDeleting(false);
    }
  };

  if (loadState.status === "loading") {
    return (
      <div aria-label="Loading preview" role="status">
        <Skeleton className="aspect-square w-full rounded-xl" />
      </div>
    );
  }
  if (loadState.status === "error") {
    return <ErrorState message={loadState.message} />;
  }

  return (
    <div>
      <div className="rounded-lg border border-border bg-surface-variant p-4 text-sm text-text-secondary">
        Your photo stays on this device while you edit — nothing is uploaded yet. Saving this
        project uploads it to secure, private storage (only you, and any artist you explicitly send
        it to, can view it). You can delete it — and its stored photo — at any time.
      </div>

      <div className="mt-4">
        {photoUrl ? (
          <OverlayEditor
            ref={editorRef}
            photoUrl={photoUrl}
            designImageUrl={selectedDesign?.thumbnail_url ?? null}
            transform={transform}
            onTransformChange={setTransform}
          />
        ) : (
          <label className="flex aspect-square w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border text-text-secondary hover:bg-surface-variant">
            Choose a hand or foot photo
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => onPhotoChange(event.target.files?.[0])}
            />
          </label>
        )}
        {photoError ? <p className="mt-2 text-sm text-danger">{photoError}</p> : null}
      </div>

      {photoUrl ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant">
            Replace photo
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => onPhotoChange(event.target.files?.[0])}
            />
          </label>
          <button
            type="button"
            onClick={() => setShowDesignPicker(true)}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            {selectedDesign ? `Design: ${selectedDesign.title}` : "Select a design"}
          </button>
        </div>
      ) : null}

      {selectedDesign ? (
        <div className="mt-4 flex flex-wrap items-center gap-4 rounded-lg border border-border bg-surface p-4">
          <button
            type="button"
            onClick={() => setTransform((t) => ({ ...t, flip_horizontal: !t.flip_horizontal }))}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Flip overlay
          </button>
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            Opacity
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={transform.opacity}
              onChange={(event) =>
                setTransform((t) => ({ ...t, opacity: Number(event.target.value) }))
              }
            />
          </label>
          <button
            type="button"
            onClick={() => setTransform(DEFAULT_OVERLAY_TRANSFORM)}
            className="text-sm text-primary hover:underline"
          >
            Reset overlay
          </button>
          <p className="text-xs text-text-secondary">
            Drag the design to move it; drag the corner handle to resize/rotate.
          </p>
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isSaving || !photoUrl}
          onClick={() => void save()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
        >
          {isSaving ? "Saving…" : "Save preview"}
        </button>
        <button
          type="button"
          disabled={isExporting || !photoUrl}
          onClick={() => void exportPreview()}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          {isExporting ? "Exporting…" : "Export image"}
        </button>
        <button
          type="button"
          disabled={isSharing || !previewId}
          onClick={() => void share()}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          {isSharing ? "Preparing…" : "Share"}
        </button>
        <button
          type="button"
          disabled={!previewId}
          onClick={() => void openSendPicker()}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          Send to artist
        </button>
        {previewId ? (
          <button
            type="button"
            disabled={isDeleting}
            onClick={() => void remove()}
            className="rounded-md border border-danger px-4 py-2 text-sm font-medium text-danger hover:bg-danger-surface disabled:opacity-50"
          >
            Delete project
          </button>
        ) : null}
      </div>

      {saveError ? <p className="mt-2 text-sm text-danger">{saveError}</p> : null}
      {exportError ? <p className="mt-2 text-sm text-danger">{exportError}</p> : null}
      {shareResult ? <p className="mt-2 text-sm text-text-secondary">{shareResult}</p> : null}
      {deleteError ? <p className="mt-2 text-sm text-danger">{deleteError}</p> : null}

      {!previewId ? (
        <p className="mt-2 text-xs text-text-secondary">
          Sharing and sending to an artist need a saved project.
        </p>
      ) : null}

      <p className="mt-4 text-sm">
        <Link href="/previews" className="text-primary hover:underline">
          My previews
        </Link>
      </p>

      {showDesignPicker ? (
        <DesignPickerDialog
          onSelect={(design) => {
            setSelectedDesign(design);
            setShowDesignPicker(false);
          }}
          onClose={() => setShowDesignPicker(false)}
        />
      ) : null}

      {showSendPicker ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-surface p-6">
            <h2 className="font-medium text-text-primary">Send to artist</h2>
            {sendSuccess ? (
              <p className="mt-3 text-sm text-text-secondary">
                Sent — check your booking messages.
              </p>
            ) : bookings === null ? (
              <p className="mt-3 text-sm text-text-secondary">Loading your bookings…</p>
            ) : bookings.length === 0 ? (
              <p className="mt-3 text-sm text-text-secondary">
                You don&apos;t have any active bookings yet.
              </p>
            ) : (
              <ul className="mt-3 flex flex-col gap-2">
                {bookings.map((booking) => (
                  <li key={booking.id}>
                    <button
                      type="button"
                      disabled={isSending}
                      onClick={() => void sendToArtist(booking.id)}
                      className="w-full rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-surface-variant disabled:opacity-50"
                    >
                      {booking.artist_display_name ?? "Artist"} — {booking.status}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {sendError ? <p className="mt-2 text-sm text-danger">{sendError}</p> : null}
            <button
              type="button"
              onClick={() => setShowSendPicker(false)}
              className="mt-4 text-sm text-text-secondary hover:underline"
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function DesignPickerDialog({
  onSelect,
  onClose,
}: {
  onSelect: (
    design: Pick<DesignSummaryData, "id" | "title" | "thumbnail_url" | "is_premium">,
  ) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [designs, setDesigns] = useState<DesignSummaryData[] | null>(null);

  useEffect(() => {
    const url = query
      ? `/api/designs/search?q=${encodeURIComponent(query)}&limit=24`
      : "/api/designs/published?limit=24";
    fetch(url)
      .then((response) => (response.ok ? response.json() : { items: [] }))
      .then((data: { items: DesignSummaryData[] }) => setDesigns(data.items))
      .catch(() => setDesigns([]));
  }, [query]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-xl bg-surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-text-primary">Select a design</h2>
          <button type="button" onClick={onClose} className="text-sm text-text-secondary">
            Close
          </button>
        </div>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search designs…"
          aria-label="Search designs"
          className="mt-3 rounded-md border border-border px-3 py-2 text-sm"
        />
        <div className="mt-4 grid grid-cols-3 gap-3 overflow-y-auto sm:grid-cols-4">
          {(designs ?? []).map((design) => (
            <button
              key={design.id}
              type="button"
              onClick={() => onSelect(design)}
              className="flex flex-col items-center gap-1 rounded-md p-1 hover:bg-surface-variant"
            >
              <span className="relative block aspect-square w-full overflow-hidden rounded-md bg-surface-variant">
                {design.thumbnail_url ? (
                  // eslint-disable-next-line @next/next/no-img-element -- small picker thumbnail
                  <img
                    src={design.thumbnail_url}
                    alt={design.title}
                    className="h-full w-full object-cover"
                  />
                ) : null}
              </span>
              <span className="w-full truncate text-xs text-text-secondary">{design.title}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

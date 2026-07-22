"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/feedback/skeleton";

// Canvas-based photo compositing (docs/hand-foot-preview.md: "compositing
// is client-side only") has no SSR value and isn't needed for first paint
// of the preview pages' shell — deferred out of the initial JS bundle.
// `ssr: false` requires a Client Component boundary, hence this wrapper
// rather than calling `dynamic()` directly from the (Server Component)
// page files.
export const PreviewStudio = dynamic(
  () => import("./preview-studio").then((m) => m.PreviewStudio),
  {
    ssr: false,
    loading: () => <Skeleton className="h-96 w-full" aria-label="Loading preview studio" />,
  },
);

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { PreviewProjectData } from "@/lib/preview-types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: PreviewProjectData[] };

export function PreviewsListView() {
  const [state, setState] = useState<State>({ status: "loading" });

  const load = useCallback(() => {
    fetch("/api/previews/mine")
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error())))
      .then((items: PreviewProjectData[]) => setState({ status: "ready", items }))
      .catch(() => setState({ status: "error", message: "Could not load your previews." }));
  }, []);

  useEffect(load, [load]);

  if (state.status === "loading") {
    return (
      <div
        role="status"
        aria-label="Loading previews"
        className="grid grid-cols-2 gap-4 sm:grid-cols-3"
      >
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="aspect-square" />
        ))}
      </div>
    );
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }
  if (state.items.length === 0) {
    return (
      <EmptyState
        title="No previews yet"
        message="Upload a photo and try a design on it — nothing is saved until you choose to."
      />
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {state.items.map((item) => (
        <Link
          key={item.id}
          href={`/previews/${item.id}`}
          className="group relative block aspect-square overflow-hidden rounded-xl bg-surface-variant"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- short-lived signed URL */}
          <img
            src={item.result_image_url ?? item.source_image_url}
            alt={item.design?.title ? `Preview with ${item.design.title}` : "Preview"}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2">
            <p className="truncate text-xs font-medium text-white">
              {item.design?.title ?? "No design selected"}
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}

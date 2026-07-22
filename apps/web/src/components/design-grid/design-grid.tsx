import type { ReactNode } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";

import { DesignCard, type DesignCardData } from "./design-card";

interface DesignGridProps {
  designs: DesignCardData[];
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  skeletonCount?: number;
}

/** Responsive image grid for browsing designs. Renders one of four states —
 * loading skeleton, error/retry, empty, or the grid itself — and never fakes
 * data for any of them (see docs/design-system.md). `error` takes priority
 * over `isLoading`/empty so a failed refresh doesn't get masked. */
export function DesignGrid({
  designs,
  isLoading = false,
  error,
  onRetry,
  emptyTitle = "No designs yet",
  emptyMessage = "Check back soon for new mehndi designs.",
  emptyAction,
  skeletonCount = 8,
}: DesignGridProps) {
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Loading designs"
        className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
      >
        {Array.from({ length: skeletonCount }).map((_, index) => (
          <Skeleton key={index} className="aspect-[3/4]" aria-label="Loading design" />
        ))}
      </div>
    );
  }

  if (designs.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} action={emptyAction} />;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {designs.map((design) => (
        <DesignCard key={design.id} design={design} />
      ))}
    </div>
  );
}

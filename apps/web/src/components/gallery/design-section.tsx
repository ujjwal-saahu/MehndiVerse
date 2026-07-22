import type { DesignCardData } from "@/components/design-grid/design-card";
import { DesignGrid } from "@/components/design-grid/design-grid";

interface DesignSectionProps {
  title: string;
  designs: DesignCardData[];
  isLoading: boolean;
  error?: string;
  onRetry?: () => void;
  emptyMessage: string;
}

/** One labeled row of the home feed (Latest / Featured / Trending) — see
 * docs/design-gallery.md#home-feed. Thin wrapper around [DesignGrid] that
 * just adds the section heading. */
export function DesignSection({
  title,
  designs,
  isLoading,
  error,
  onRetry,
  emptyMessage,
}: DesignSectionProps) {
  return (
    <section aria-labelledby={`section-${title}`} className="mt-10">
      <h2 id={`section-${title}`} className="font-display text-xl font-semibold text-text-primary">
        {title}
      </h2>
      <div className="mt-4">
        <DesignGrid
          designs={designs}
          isLoading={isLoading}
          error={error}
          onRetry={onRetry}
          emptyTitle={`No ${title.toLowerCase()} yet`}
          emptyMessage={emptyMessage}
          skeletonCount={4}
        />
      </div>
    </section>
  );
}

import Image from "next/image";

import type { ArtistSummaryData } from "@/lib/gallery-types";

export function ArtistSummaryCard({ artist }: { artist: ArtistSummaryData }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4">
      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full bg-surface-variant">
        {artist.avatar_url ? (
          <Image src={artist.avatar_url} alt="" fill sizes="48px" className="object-cover" />
        ) : null}
      </div>
      <div className="min-w-0">
        <p className="truncate font-medium text-text-primary">{artist.display_name}</p>
        {artist.headline ? (
          <p className="truncate text-sm text-text-secondary">{artist.headline}</p>
        ) : null}
        <p className="text-xs text-text-secondary">
          {artist.rating_count > 0
            ? `★ ${artist.rating_average.toFixed(1)} (${artist.rating_count})`
            : "No reviews yet"}
        </p>
      </div>
    </div>
  );
}

import Image from "next/image";
import Link from "next/link";

import type { CollectionData } from "@/lib/collection-types";

/** A single collection tile in the collections grid — mirrors DesignCard's
 * image-forward, placeholder-when-empty treatment. */
export function CollectionCard({ collection }: { collection: CollectionData }) {
  return (
    <Link
      href={`/collections/${collection.id}`}
      className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring rounded-xl"
    >
      <div className="group relative aspect-[3/4] overflow-hidden rounded-xl bg-surface-variant shadow-sm transition-shadow hover:shadow-lg">
        {collection.cover_image_url ? (
          <Image
            src={collection.cover_image_url}
            alt={`${collection.name} collection cover`}
            fill
            sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
            className="object-cover transition-transform duration-200 ease-out group-hover:scale-105"
          />
        ) : (
          <div
            role="img"
            aria-label={`${collection.name} — no cover image yet`}
            className="flex h-full w-full items-center justify-center"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="h-10 w-10 text-text-secondary opacity-40"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Z"
              />
            </svg>
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3">
          <p className="truncate text-sm font-medium text-white">{collection.name}</p>
          <p className="text-xs text-white/80">
            {collection.item_count} {collection.item_count === 1 ? "design" : "designs"} ·{" "}
            {collection.is_private ? "Private" : "Public"}
          </p>
        </div>
      </div>
    </Link>
  );
}

import Image from "next/image";
import Link from "next/link";

export interface DesignCardData {
  id: string;
  title: string;
  imageUrl: string | null;
  artistName?: string;
  href?: string;
}

/** A single image-forward design tile. Deliberately image-heavy with
 * minimal chrome — see docs/design-system.md's "image-focused" direction.
 * `imageUrl` is nullable because a design's thumbnail may still be
 * processing (or have failed) server-side — see
 * docs/design-gallery.md#image-upload-pipeline — in which case a plain
 * placeholder is shown instead of a broken image. */
export function DesignCard({ design }: { design: DesignCardData }) {
  const altText = design.artistName
    ? `${design.title} mehndi design by ${design.artistName}`
    : `${design.title} mehndi design`;

  const content = (
    <div className="group relative aspect-[3/4] overflow-hidden rounded-xl bg-surface-variant shadow-sm transition-shadow hover:shadow-lg">
      {design.imageUrl ? (
        <Image
          src={design.imageUrl}
          alt={altText}
          fill
          sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
          className="object-cover transition-transform duration-200 ease-out group-hover:scale-105"
        />
      ) : (
        <div
          role="img"
          aria-label={`${altText} — image not yet available`}
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
              d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm0 12 5-6 4 4 3-3 4 5"
            />
            <circle cx="8" cy="9" r="1.5" />
          </svg>
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3">
        <p className="truncate text-sm font-medium text-white">{design.title}</p>
        {design.artistName ? (
          <p className="truncate text-xs text-white/80">by {design.artistName}</p>
        ) : null}
      </div>
    </div>
  );

  if (!design.href) return content;

  return (
    <Link
      href={design.href}
      className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring rounded-xl"
    >
      {content}
    </Link>
  );
}

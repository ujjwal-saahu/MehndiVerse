import Link from "next/link";

import { PortfolioManagerView } from "./portfolio-manager-view";

export default function ArtistPortfolioPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-text-primary">My portfolio</h1>
          <p className="mt-1 text-text-secondary">Manage your designs, images, and categories.</p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/artist/portfolio/analytics"
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Analytics
          </Link>
          <Link
            href="/artist/portfolio/new"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
          >
            New design
          </Link>
        </div>
      </div>
      <div className="mt-6">
        <PortfolioManagerView />
      </div>
    </div>
  );
}

import { DiscoverView } from "@/components/gallery/discover-view";

export default function DiscoverPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Discover</h1>
      <p className="mt-2 text-text-secondary">
        Browse bridal and everyday mehndi designs from artists on MehndiVerse.
      </p>
      <div className="mt-8">
        <DiscoverView />
      </div>
    </div>
  );
}

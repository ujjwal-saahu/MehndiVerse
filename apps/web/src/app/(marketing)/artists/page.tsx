import { ArtistDirectoryView } from "./artist-directory-view";

export default function ArtistDirectoryPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Find an artist</h1>
      <p className="mt-2 text-text-secondary">
        Browse verified mehndi artists by location, service, and rating.
      </p>
      <div className="mt-6">
        <ArtistDirectoryView />
      </div>
    </div>
  );
}

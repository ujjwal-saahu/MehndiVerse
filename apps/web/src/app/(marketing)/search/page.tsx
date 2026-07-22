import { SearchView } from "@/components/search/search-view";

export default function SearchPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Search</h1>
      <p className="mt-2 text-text-secondary">
        Find mehndi designs by keyword, style, occasion, artist, and more.
      </p>
      <div className="mt-8">
        <SearchView />
      </div>
    </div>
  );
}

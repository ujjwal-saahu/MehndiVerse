import { ArtistPortfolioGrid } from "./artist-portfolio-grid";

export default async function ArtistFullPortfolioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Portfolio</h1>
      <div className="mt-6">
        <ArtistPortfolioGrid artistId={id} />
      </div>
    </div>
  );
}

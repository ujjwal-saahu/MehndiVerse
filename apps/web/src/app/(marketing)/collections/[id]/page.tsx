import { CollectionDetailView } from "@/components/collections/collection-detail-view";

export default async function CollectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <CollectionDetailView collectionId={id} />
    </div>
  );
}

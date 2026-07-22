import { DesignDetailView } from "@/components/gallery/design-detail-view";

export default async function DesignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <DesignDetailView designId={id} />
    </div>
  );
}

import { CollectionsView } from "@/components/collections/collections-view";

export default function CollectionsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Collections</h1>
      <p className="mt-2 text-text-secondary">
        Organize designs into your own curated collections and share the public ones.
      </p>
      <div className="mt-8">
        <CollectionsView />
      </div>
    </div>
  );
}

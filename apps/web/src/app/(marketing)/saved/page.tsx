import { SavedDesignsView } from "@/components/collections/saved-designs-view";

export default function SavedDesignsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Saved Designs</h1>
      <p className="mt-2 text-text-secondary">Designs you&apos;ve quick-saved for later.</p>
      <div className="mt-8">
        <SavedDesignsView />
      </div>
    </div>
  );
}

import { AvailabilityManagerView } from "./availability-manager-view";

export default function ArtistAvailabilityPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Availability</h1>
      <p className="mt-1 text-text-secondary">
        Set your weekly hours, time off, and scheduling defaults.
      </p>
      <div className="mt-6">
        <AvailabilityManagerView />
      </div>
    </div>
  );
}

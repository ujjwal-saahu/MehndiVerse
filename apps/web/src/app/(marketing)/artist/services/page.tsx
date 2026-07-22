import { ServicesManagerView } from "./services-manager-view";

export default function ArtistServicesPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">My services</h1>
      <p className="mt-1 text-text-secondary">
        Manage what customers see and can request when they visit your profile.
      </p>
      <div className="mt-6">
        <ServicesManagerView />
      </div>
    </div>
  );
}

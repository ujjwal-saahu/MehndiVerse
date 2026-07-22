import { NotificationsView } from "./notifications-view";

export default function NotificationsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Notifications</h1>
      <div className="mt-6">
        <NotificationsView />
      </div>
    </div>
  );
}

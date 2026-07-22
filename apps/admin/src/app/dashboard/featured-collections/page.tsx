import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { FeaturedCollectionsView } from "./featured-collections-view";

export default async function FeaturedCollectionsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        Featured Collections
      </h1>
      <div className="mt-6">
        <FeaturedCollectionsView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { TagsView } from "./tags-view";

export default async function TagsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Tags</h1>
      <div className="mt-6">
        <TagsView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

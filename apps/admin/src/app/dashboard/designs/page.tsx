import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { DesignsView } from "./designs-view";

export default async function DesignsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Design Moderation</h1>
      <div className="mt-6">
        <DesignsView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

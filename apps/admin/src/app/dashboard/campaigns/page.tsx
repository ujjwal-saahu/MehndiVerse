import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { CampaignsView } from "./campaigns-view";

export default async function CampaignsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        Notification Campaigns
      </h1>
      <div className="mt-6">
        <CampaignsView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { BannersView } from "./banners-view";

export default async function BannersPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Promotional Banners</h1>
      <div className="mt-6">
        <BannersView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { RefundsView } from "./refunds-view";

export default async function RefundsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Refunds</h1>
      <div className="mt-6">
        <RefundsView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

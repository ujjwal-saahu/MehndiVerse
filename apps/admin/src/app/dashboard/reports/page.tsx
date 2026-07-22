import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { ReportsQueueView } from "./reports-queue-view";

export default async function ReportsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Reports</h1>
      <div className="mt-6">
        <ReportsQueueView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

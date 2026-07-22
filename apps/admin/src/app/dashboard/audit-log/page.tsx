import { DashboardShell } from "@/components/layout/dashboard-shell";
import { requireEditStaffUser } from "@/lib/current-staff-user";

import { AuditLogView } from "./audit-log-view";

export default async function AuditLogPage() {
  const user = await requireEditStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Audit Log</h1>
      <div className="mt-6">
        <AuditLogView />
      </div>
    </DashboardShell>
  );
}

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { requireSuperAdminUser } from "@/lib/current-staff-user";

import { RoleManagementView } from "./role-management-view";

export default async function RoleManagementPage() {
  const user = await requireSuperAdminUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Role Management</h1>
      <p className="mt-2 text-sm text-text-secondary">
        Super-admin-only — see docs/admin-dashboard.md#super-admin-only-modules. You cannot change
        your own role.
      </p>
      <div className="mt-6">
        <RoleManagementView currentUserId={user.id} />
      </div>
    </DashboardShell>
  );
}

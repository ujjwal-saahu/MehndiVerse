import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { UsersView } from "./users-view";

export default async function UsersPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Users</h1>
      <div className="mt-6">
        <UsersView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

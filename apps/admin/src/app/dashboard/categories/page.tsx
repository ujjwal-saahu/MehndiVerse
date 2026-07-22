import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { CategoriesView } from "./categories-view";

export default async function CategoriesPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Categories</h1>
      <div className="mt-6">
        <CategoriesView canAct={canEdit(user.role)} />
      </div>
    </DashboardShell>
  );
}

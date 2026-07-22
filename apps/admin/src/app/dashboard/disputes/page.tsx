import { DashboardShell } from "@/components/layout/dashboard-shell";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";

import { BookingsView } from "../bookings/bookings-view";

export default async function DisputesPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Disputes</h1>
      <div className="mt-6">
        <BookingsView canAct={canEdit(user.role)} mode="disputes" />
      </div>
    </DashboardShell>
  );
}

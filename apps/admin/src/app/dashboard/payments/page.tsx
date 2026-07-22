import { DashboardShell } from "@/components/layout/dashboard-shell";
import { requireStaffUser } from "@/lib/current-staff-user";

import { PaymentsView } from "./payments-view";

export default async function PaymentsPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Payments</h1>
      <div className="mt-6">
        <PaymentsView />
      </div>
    </DashboardShell>
  );
}

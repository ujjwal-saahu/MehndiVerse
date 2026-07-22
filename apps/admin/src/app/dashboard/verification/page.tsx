import { DashboardShell } from "@/components/layout/dashboard-shell";
import { requireStaffUser } from "@/lib/current-staff-user";

import { VerificationQueueView } from "./verification-queue-view";

export default async function VerificationPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Artist Verification</h1>
      <div className="mt-6">
        <VerificationQueueView />
      </div>
    </DashboardShell>
  );
}

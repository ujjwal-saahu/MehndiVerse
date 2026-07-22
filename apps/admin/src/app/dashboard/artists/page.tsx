import { DashboardShell } from "@/components/layout/dashboard-shell";
import { requireStaffUser } from "@/lib/current-staff-user";

import { VerificationQueueView } from "../verification/verification-queue-view";

/** "Artist Management" — browsing and acting on any artist regardless of
 * verification status, distinct from the Artist Verification module's
 * pending-review-first default. Both share the same backend queue endpoint
 * and the same detail page (`/dashboard/verification/{id}`) — see
 * docs/admin-dashboard.md#artist-management. */
export default async function ArtistManagementPage() {
  const user = await requireStaffUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Artist Management</h1>
      <div className="mt-6">
        <VerificationQueueView defaultFilterIndex={5} />
      </div>
    </DashboardShell>
  );
}

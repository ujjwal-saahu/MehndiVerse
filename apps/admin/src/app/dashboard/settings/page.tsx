import { DashboardShell } from "@/components/layout/dashboard-shell";
import { requireSuperAdminUser } from "@/lib/current-staff-user";

import { SettingsView } from "./settings-view";

export default async function SettingsPage() {
  const user = await requireSuperAdminUser();

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">System Settings</h1>
      <div className="mt-6">
        <SettingsView />
      </div>
    </DashboardShell>
  );
}

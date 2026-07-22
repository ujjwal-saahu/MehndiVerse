import { cookies } from "next/headers";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import type { DashboardOverviewData } from "@/lib/admin-types";
import { backendFetch } from "@/lib/backend";
import { requireStaffUser } from "@/lib/current-staff-user";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

const STATS: { key: keyof DashboardOverviewData; label: string }[] = [
  { key: "pending_artist_verifications", label: "Pending Artist Verifications" },
  { key: "pending_reports", label: "Pending Reports" },
  { key: "pending_refunds", label: "Pending Refunds" },
  { key: "disputed_bookings", label: "Disputed Bookings" },
  { key: "total_users", label: "Total Users" },
  { key: "total_artists", label: "Total Artists" },
  { key: "total_designs", label: "Total Designs" },
  { key: "total_bookings", label: "Total Bookings" },
];

export default async function DashboardPage() {
  const user = await requireStaffUser();
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;

  const response = await backendFetch("/admin/dashboard/overview", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const overview: DashboardOverviewData | null = response.ok ? await response.json() : null;

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">Dashboard</h1>
      <p className="mt-2 text-text-secondary">
        Signed in as {user.email} ({user.role})
      </p>

      {overview ? (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((stat) => (
            <div key={stat.key} className="rounded-xl border border-border bg-surface p-4">
              <p className="text-sm text-text-secondary">{stat.label}</p>
              <p className="mt-1 font-display text-2xl font-semibold text-text-primary">
                {overview[stat.key]}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p role="alert" className="mt-6 text-sm text-danger">
          Could not load the dashboard overview. Try refreshing the page.
        </p>
      )}
    </DashboardShell>
  );
}

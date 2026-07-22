import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "./backend";
import { ACCESS_TOKEN_COOKIE } from "./session-cookies";

const STAFF_ROLES = new Set(["moderator", "admin", "super_admin"]);
const EDIT_STAFF_ROLES = new Set(["admin", "super_admin"]);

export interface CurrentStaffUser {
  id: string;
  email: string;
  role: string;
}

/** Every dashboard page calls this at the top — it re-validates the session
 * and staff role server-side on each request (never trusts the client) and
 * redirects to /login otherwise. See docs/authentication.md. */
export async function requireStaffUser(): Promise<CurrentStaffUser> {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    redirect("/login");
  }

  const user = (await response.json()) as CurrentStaffUser;
  if (!STAFF_ROLES.has(user.role)) {
    redirect("/login");
  }

  return user;
}

/** Same as [requireStaffUser], but for pages/actions restricted to
 * admin/super_admin (moderators get redirected to the dashboard home
 * rather than logged out — they're valid staff, just not permitted here).
 * See docs/admin-dashboard.md#server-side-permission-checks. */
export async function requireEditStaffUser(): Promise<CurrentStaffUser> {
  const user = await requireStaffUser();
  if (!EDIT_STAFF_ROLES.has(user.role)) {
    redirect("/dashboard");
  }
  return user;
}

/** Same again, restricted to super_admin only — system settings and
 * role management (see docs/admin-dashboard.md#super-admin-only-modules). */
export async function requireSuperAdminUser(): Promise<CurrentStaffUser> {
  const user = await requireStaffUser();
  if (user.role !== "super_admin") {
    redirect("/dashboard");
  }
  return user;
}

export function canEdit(role: string): boolean {
  return EDIT_STAFF_ROLES.has(role);
}

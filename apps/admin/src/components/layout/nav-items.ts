export interface NavItem {
  label: string;
  href: string;
  /** Effective roles (see docs/authentication.md#1) permitted to see this
   * item. Never trust a role the client already has cached — the sidebar
   * only *hides* items for UX; every destination page independently
   * re-checks the role server-side. */
  roles: readonly string[];
}

const VIEW_ROLES = ["moderator", "admin", "super_admin"] as const;
const EDIT_ROLES = ["admin", "super_admin"] as const;

// 19 modules — see docs/admin-dashboard.md#dashboard-modules. Order
// roughly follows the phase's own module list.
export const NAV_ITEMS: readonly NavItem[] = [
  { label: "Dashboard", href: "/dashboard", roles: VIEW_ROLES },
  { label: "Users", href: "/dashboard/users", roles: VIEW_ROLES },
  { label: "Artist Verification", href: "/dashboard/verification", roles: VIEW_ROLES },
  { label: "Artist Management", href: "/dashboard/artists", roles: VIEW_ROLES },
  { label: "Design Moderation", href: "/dashboard/designs", roles: VIEW_ROLES },
  { label: "Categories", href: "/dashboard/categories", roles: VIEW_ROLES },
  { label: "Tags", href: "/dashboard/tags", roles: VIEW_ROLES },
  { label: "Bookings", href: "/dashboard/bookings", roles: VIEW_ROLES },
  { label: "Payments", href: "/dashboard/payments", roles: VIEW_ROLES },
  { label: "Refunds", href: "/dashboard/refunds", roles: VIEW_ROLES },
  { label: "Reports", href: "/dashboard/reports", roles: VIEW_ROLES },
  { label: "Disputes", href: "/dashboard/disputes", roles: VIEW_ROLES },
  { label: "Review Moderation", href: "/dashboard/reviews", roles: VIEW_ROLES },
  { label: "Promotional Banners", href: "/dashboard/banners", roles: VIEW_ROLES },
  { label: "Featured Collections", href: "/dashboard/featured-collections", roles: VIEW_ROLES },
  { label: "Notification Campaigns", href: "/dashboard/campaigns", roles: VIEW_ROLES },
  { label: "Audit Log", href: "/dashboard/audit-log", roles: EDIT_ROLES },
  { label: "Settings", href: "/dashboard/settings", roles: ["super_admin"] },
  { label: "Role Management", href: "/dashboard/roles", roles: ["super_admin"] },
] as const;

export function navItemsForRole(role: string): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

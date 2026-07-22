import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

import { loginAs } from "../helpers/auth";
import { seedUser } from "../helpers/seed";

// See docs/test-matrix.md#end-to-end-admin-moderation-journey.
test.describe("admin moderation journey", () => {
  test("a non-staff user is redirected away from the dashboard", async ({ page, context }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "customer" });
    await loginAs(context, { app: "admin", port: 3001, userId, email });

    // `requireStaffUser()` (apps/admin/src/lib/current-staff-user.ts) is a
    // *page-level* server-side check, on top of the middleware's presence-
    // only session gate — a customer session redirects to /login here.
    await page.goto("http://localhost:3001/dashboard/reports");
    await expect(page).toHaveURL(/\/login/);
  });

  test("a moderator can reach the reports queue", async ({ page, context }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "moderator", displayName: "E2E Moderator" });
    await loginAs(context, { app: "admin", port: 3001, userId, email });

    await page.goto("http://localhost:3001/dashboard/reports");

    await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
  });

  test("signed-out visitor is redirected to the admin login page", async ({ page }) => {
    await page.goto("http://localhost:3001/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});

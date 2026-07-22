import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

import { loginAs, signExpiredAccessToken } from "../helpers/auth";
import { seedUser } from "../helpers/seed";

// Phase 30 QA gaps flagged in docs/test-matrix.md as "manual"/"not device-
// tested" — the three checks below are the pieces of that gap that a real
// browser (not jsdom/component tests) can actually automate: an expired-
// but-validly-signed session cookie, a throttled network, and an RTL
// locale, all against the real running app (not a mock).
test.describe("resilience and accessibility", () => {
  test("an expired session cookie redirects to login instead of showing stale data", async ({
    page,
    context,
  }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "customer", displayName: "E2E Expired" });
    await loginAs(context, {
      app: "web",
      port: 3000,
      userId,
      email,
      token: signExpiredAccessToken(userId, email),
    });

    await page.goto("http://localhost:3000/account");

    await expect(page).toHaveURL(/\/login/);
  });

  test('an RTL locale renders the page with dir="rtl"', async ({ page, context }) => {
    await context.addCookies([{ name: "mv_locale", value: "ar", domain: "localhost", path: "/" }]);

    await page.goto("http://localhost:3000/");

    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });

  test("discover still loads correctly on a throttled connection", async ({ page, context }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "customer", displayName: "E2E Slow Network" });
    await loginAs(context, { app: "web", port: 3000, userId, email });

    // Adds artificial latency to every request MehndiVerse's own servers
    // handle, simulating a slow network without needing real device/network
    // hardware (docs/test-matrix.md's "Real device / real network
    // conditions" gap) — the assertion is simply that the page still
    // reaches a correct, non-hung state, just later.
    await page.route("**/*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 200));
      await route.continue();
    });

    await page.goto("http://localhost:3000/discover", { timeout: 20_000 });

    await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible({ timeout: 20_000 });
  });
});

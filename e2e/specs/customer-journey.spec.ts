import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

import { loginAs } from "../helpers/auth";
import { seedUser } from "../helpers/seed";

// See docs/test-matrix.md#end-to-end-customer-journey.
test.describe("customer journey", () => {
  test("signed-out visitor can browse discover without a session", async ({ page }) => {
    await page.goto("http://localhost:3000/");
    await page.getByLabel("Primary").getByRole("link", { name: "Log in" }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("authenticated customer can reach account and discover pages", async ({
    page,
    context,
  }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "customer", displayName: "E2E Customer" });
    await loginAs(context, { app: "web", port: 3000, userId, email });

    await page.goto("http://localhost:3000/account");
    await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();

    await page.goto("http://localhost:3000/discover");
    await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible();
  });
});

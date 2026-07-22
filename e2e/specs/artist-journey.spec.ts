import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

import { loginAs } from "../helpers/auth";
import { seedArtistProfile, seedUser } from "../helpers/seed";

// See docs/test-matrix.md#end-to-end-artist-journey.
test.describe("artist journey", () => {
  test("verified artist reaches their booking inbox", async ({ page, context }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "artist", displayName: "E2E Artist" });
    seedArtistProfile({ userId, id: randomUUID() });
    await loginAs(context, { app: "web", port: 3000, userId, email });

    await page.goto("http://localhost:3000/artist/bookings");

    await expect(page.getByRole("heading", { name: "Booking inbox" })).toBeVisible();
  });

  test("an artist without a verified profile is redirected to onboarding", async ({
    page,
    context,
  }) => {
    const userId = randomUUID();
    const email = `${userId}@e2e.test`;
    seedUser({ id: userId, email, role: "artist", displayName: "E2E Unverified Artist" });
    // Deliberately no seedArtistProfile() call — no artist_profiles row.
    await loginAs(context, { app: "web", port: 3000, userId, email });

    await page.goto("http://localhost:3000/artist/bookings");

    await expect(page).toHaveURL(/\/artist\/onboarding/);
  });
});

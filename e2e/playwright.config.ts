import { defineConfig } from "@playwright/test";

// End-to-end journeys — see docs/test-matrix.md#end-to-end-journeys.
// Runs against locally-started dev servers (apps/api on :8000, apps/web on
// :3000, apps/admin on :3001) — not started by this config; see
// docs/test-matrix.md for how to run these.
export default defineConfig({
  testDir: "./specs",
  timeout: 30_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    trace: "retain-on-failure",
  },
  // Every spec hardcodes its own full URL (localhost:3000 for apps/web,
  // :3001 for apps/admin) rather than relying on a per-project baseURL —
  // a single project keeps each spec file running exactly once.
});

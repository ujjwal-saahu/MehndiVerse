// Mints local test-session JWTs for the personas seeded by
// apps/api/scripts/seed_local_data.py — see docs/visual-testing-guide.md.
//
// Real Supabase Auth can't be exercised locally (only placeholder
// credentials exist — see docs/test-matrix.md#excluded-flows). This mints
// an HS256 JWT the same way apps/api's own test suite
// (tests/auth/conftest.py::sign_token) and e2e/helpers/auth.ts do: signed
// locally with the backend's own SUPABASE_JWT_SECRET, which the backend
// verifies without ever calling Supabase. A correctly-signed token is
// indistinguishable from a real one to the app. Never prints the secret
// itself, only the resulting per-persona tokens (each one is a session
// credential for a disposable local test account, not a secret in itself).
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";

function loadEnvValue(path, key) {
  const content = readFileSync(path, "utf8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.startsWith(`${key}=`)) return trimmed.slice(key.length + 1);
  }
  return null;
}

const secret =
  loadEnvValue("apps/api/.env", "SUPABASE_JWT_SECRET") ?? "placeholder-jwt-secret-change-me";

function base64url(input) {
  return Buffer.from(input)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function signToken(userId, email) {
  const header = { alg: "HS256", typ: "JWT" };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    sub: userId,
    email,
    aud: "authenticated",
    role: "authenticated",
    iat: now,
    exp: now + 60 * 60 * 24 * 7, // 7 days — local testing convenience only
  };
  const unsigned = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(payload))}`;
  const signature = createHmac("sha256", secret).update(unsigned).digest();
  return `${unsigned}.${base64url(signature)}`;
}

// user_id values printed by seed_local_data.py — update if you re-seed a
// fresh (empty) database and the printed ids differ.
const PERSONAS = [
  { key: "customer", userId: process.argv[2], email: "customer@mehndiverse.test" },
  { key: "artist (unverified)", userId: process.argv[3], email: "artist@mehndiverse.test" },
  {
    key: "verified_artist",
    userId: process.argv[4],
    email: "verified-artist@mehndiverse.test",
  },
  { key: "moderator", userId: process.argv[5], email: "moderator@mehndiverse.test" },
  { key: "admin", userId: process.argv[6], email: "admin@mehndiverse.test" },
];

if (PERSONAS.some((p) => !p.userId)) {
  console.error(
    "Usage: node scripts/mint_local_sessions.mjs <customerId> <artistId> <verifiedArtistId> <moderatorId> <adminId>\n" +
      "(the 5 UUIDs printed by `python scripts/seed_local_data.py`)",
  );
  process.exit(1);
}

for (const persona of PERSONAS) {
  const token = signToken(persona.userId, persona.email);
  console.log(`\n=== ${persona.key} (${persona.email}) ===`);
  console.log(`mv_access_token = ${token}`);
}
console.log(
  "\nIn the browser: DevTools -> Application -> Cookies -> localhost:3000 (or :3001 for " +
    "admin) -> add a cookie named mv_access_token (mv_admin_access_token for admin) with the " +
    "value above, domain 'localhost', path '/'. Then reload.",
);

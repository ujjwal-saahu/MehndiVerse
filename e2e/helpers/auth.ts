import { createHmac, randomUUID } from "node:crypto";
import type { BrowserContext } from "@playwright/test";

// Real Supabase auth can't be exercised here (only placeholder credentials
// exist in this environment — see docs/test-matrix.md#required-manual-
// tests). Instead, mints a JWT the same way the backend's own test suite
// does (tests/auth/conftest.py::sign_token) — both verify the signature
// locally against SUPABASE_JWT_SECRET, never call Supabase, so a
// correctly-signed token is indistinguishable from a real one to either
// app. This exercises real app code (middleware, route handlers, backend
// authorization), not a mock.
const JWT_SECRET = process.env.E2E_JWT_SECRET ?? "placeholder-jwt-secret-change-me";

function base64url(input: Buffer | string): string {
  return Buffer.from(input)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function signToken(userId: string, email: string, expiresAtSeconds: number): string {
  const header = { alg: "HS256", typ: "JWT" };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    sub: userId,
    email,
    aud: "authenticated",
    role: "authenticated",
    iat: now,
    exp: expiresAtSeconds,
  };
  const unsigned = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(payload))}`;
  const signature = createHmac("sha256", JWT_SECRET).update(unsigned).digest();
  return `${unsigned}.${base64url(signature)}`;
}

export function signAccessToken(userId: string, email: string): string {
  return signToken(userId, email, Math.floor(Date.now() / 1000) + 3600);
}

/** A validly-signed token whose `exp` is already in the past — the backend
 * rejects this the same way it would a real expired Supabase session
 * (`decode_access_token` checks `exp`), letting the expired-session e2e
 * spec exercise real backend/page code rather than mocking a 401. */
export function signExpiredAccessToken(userId: string, email: string): string {
  return signToken(userId, email, Math.floor(Date.now() / 1000) - 3600);
}

/** Injects a session cookie for `userId`/`email` into `context` for the
 * given app ("web" -> mv_access_token, "admin" -> mv_admin_access_token —
 * see apps/{web,admin}/src/lib/session-cookies.ts) and port. Also creates
 * a fresh random user id by default so tests don't collide with each
 * other's data. */
export async function loginAs(
  context: BrowserContext,
  params: {
    app: "web" | "admin";
    port: number;
    userId?: string;
    email?: string;
    /** Override the minted token (e.g. `signExpiredAccessToken`'s result) —
     * used by the expired-session e2e spec. Defaults to a normal, valid
     * `signAccessToken()` token. */
    token?: string;
  },
): Promise<{ userId: string; email: string }> {
  const userId = params.userId ?? randomUUID();
  const email = params.email ?? `${userId}@e2e.test`;
  const token = params.token ?? signAccessToken(userId, email);
  const cookieName = params.app === "admin" ? "mv_admin_access_token" : "mv_access_token";

  await context.addCookies([
    {
      name: cookieName,
      value: token,
      domain: "localhost",
      path: "/",
    },
  ]);
  return { userId, email };
}

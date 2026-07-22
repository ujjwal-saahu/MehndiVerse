import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

const PUBLIC_PATHS = new Set(["/login"]);
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** CSRF defense-in-depth, mirrors apps/web/src/middleware.ts — see
 * docs/security-review.md#csrf. Staff sessions can change role/payment/
 * moderation state, so cross-origin mutation protection matters here at
 * least as much as on the customer app. */
function isCrossOriginMutation(request: NextRequest): boolean {
  if (!UNSAFE_METHODS.has(request.method)) return false;

  const origin = request.headers.get("origin");
  if (origin) {
    return origin !== request.nextUrl.origin;
  }
  const referer = request.headers.get("referer");
  if (referer) {
    try {
      return new URL(referer).origin !== request.nextUrl.origin;
    } catch {
      return true;
    }
  }
  return false;
}

/** Per-request nonce — see apps/web/src/middleware.ts's identical helper
 * for why this exists (a static `script-src 'self'` silently breaks
 * Next.js's own inline hydration script; found via Phase 26 E2E testing). */
function buildCsp(nonce: string): string {
  const scriptSrc =
    process.env.NODE_ENV === "production"
      ? `script-src 'self' 'nonce-${nonce}'`
      : `script-src 'self' 'nonce-${nonce}' 'unsafe-eval'`;
  return [
    "default-src 'self'",
    "img-src 'self' data: https://*.supabase.co",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

/** Presence-only gate for the whole admin app (staff-only — there is no
 * public area). Actual role enforcement (moderator/admin/super_admin) happens
 * server-side against the backend on every page load and API call — this
 * middleware only prevents an obviously-unauthenticated visitor from seeing
 * dashboard UI flash before redirecting. See docs/authentication.md#2. */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/api/") && isCrossOriginMutation(request)) {
    return NextResponse.json({ message: "Cross-origin request rejected." }, { status: 403 });
  }

  const nonce = crypto.randomUUID().replace(/-/g, "");
  const csp = buildCsp(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);

  if (!PUBLIC_PATHS.has(pathname) && !pathname.startsWith("/api/auth")) {
    const hasSession = request.cookies.has(ACCESS_TOKEN_COOKIE);
    if (!hasSession) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      const response = NextResponse.redirect(loginUrl);
      response.headers.set("Content-Security-Policy", csp);
      return response;
    }
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

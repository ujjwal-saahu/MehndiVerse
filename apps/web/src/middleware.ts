import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

const PROTECTED_PREFIXES = [
  "/account",
  "/discover",
  "/designs",
  "/search",
  "/collections",
  "/saved",
  "/artist",
  "/artists",
  "/admin",
];

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** CSRF defense-in-depth for the `/api/*` Route Handlers, on top of the
 * session cookies' `SameSite=Lax` (see lib/session-cookies.ts) — Lax
 * already blocks the cookie from riding along on a cross-site POST, but
 * this catches it explicitly (and covers browsers/configurations where a
 * `SameSite` attribute is ignored) by rejecting any state-changing request
 * whose `Origin` doesn't match this app's own origin. See
 * docs/security-review.md#csrf. */
function isCrossOriginMutation(request: NextRequest): boolean {
  if (!UNSAFE_METHODS.has(request.method)) return false;

  const origin = request.headers.get("origin");
  if (origin) {
    return origin !== request.nextUrl.origin;
  }
  // No Origin header (older browser, or a same-origin request that omitted
  // it) — fall back to Referer. If neither is present, there's nothing to
  // check against; let it through rather than breaking a legitimate
  // request on a false negative.
  const referer = request.headers.get("referer");
  if (referer) {
    try {
      return new URL(referer).origin !== request.nextUrl.origin;
    } catch {
      return true; // an unparseable Referer is itself suspicious
    }
  }
  return false;
}

/** Per-request nonce so `script-src` can stay off `'unsafe-inline'` while
 * still allowing Next.js's own required inline hydration scripts — see
 * next.config.ts's comment and docs/test-matrix.md's "defects fixed"
 * section for what broke without this (every streamed page silently stuck
 * on its loading skeleton, only visible with JS execution + CSP
 * enforcement, i.e. only caught by a real-browser E2E test). Follows
 * Next.js's documented nonce pattern: the nonce goes on both an
 * `x-nonce` request header (so Server Components can read it via
 * `headers()` if they ever need to nonce their own inline scripts) and
 * the response's `Content-Security-Policy` header. No `'strict-dynamic'` —
 * that requires precisely propagating the nonce to every dynamically
 * injected script too, more than this phase can fully verify; plain
 * `'self' 'nonce-...'` is the safer, directly-testable choice. */
function buildCsp(nonce: string): string {
  // React's dev-mode debugging tools call eval() (component stack
  // reconstruction) — never in production. Gating this the same way
  // app/core/security_headers.py gates HSTS by environment.
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

/** Presence-only gate: redirects to /login if the session cookie is
 * missing. This is a navigation convenience, not the security boundary —
 * every backend request still validates the token independently (see
 * app/api/deps.py::get_current_user). */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/api/")) {
    if (isCrossOriginMutation(request)) {
      return NextResponse.json({ message: "Cross-origin request rejected." }, { status: 403 });
    }
    return NextResponse.next();
  }

  const nonce = crypto.randomUUID().replace(/-/g, "");
  const csp = buildCsp(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);

  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (isProtected && !request.cookies.has(ACCESS_TOKEN_COOKIE)) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    const response = NextResponse.redirect(loginUrl);
    response.headers.set("Content-Security-Policy", csp);
    return response;
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

import type { NextConfig } from "next";

// See docs/security-review.md#security-headers and docs/test-matrix.md's
// "defects fixed" section. Content-Security-Policy moved to middleware.ts
// — it needs a per-request nonce (see below), which a static config here
// can't produce. `script-src 'self'` with no nonce/`unsafe-inline` was
// found via Phase 26 E2E testing to block Next.js's own required inline
// hydration script, hanging every streamed page on its loading skeleton
// forever in any CSP-enforcing browser (Playwright caught it; a plain
// `curl` never would have, since it doesn't execute JS or enforce CSP).
const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
];

const nextConfig: NextConfig = {
  transpilePackages: ["@mehndiverse/contracts", "@mehndiverse/design-tokens"],
  // Self-contained `.next/standalone` output — see Dockerfile and
  // docs/deployment.md#api-web-admin. Only affects `next build`'s output
  // shape, not `next dev`.
  output: "standalone",
  images: {
    remotePatterns: [
      // Design/portfolio/avatar images are served from Supabase Storage —
      // this was missing entirely (next/image silently rejects any host not
      // explicitly allow-listed), matching the `https://*.supabase.co`
      // already trusted by middleware.ts's CSP `img-src`.
      { protocol: "https", hostname: "*.supabase.co" },
      // Local visual-testing seed images only (docs/visual-testing-guide.md)
      // — served from this same app's own `public/seed/`.
      { protocol: "http", hostname: "localhost", port: "3000" },
    ],
  },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;

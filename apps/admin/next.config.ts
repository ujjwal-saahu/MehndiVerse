import type { NextConfig } from "next";

// See docs/security-review.md#security-headers and docs/test-matrix.md's
// "defects fixed" section. Content-Security-Policy moved to middleware.ts
// — same fix as apps/web (see its next.config.ts comment for the defect
// this was found to cause: `script-src 'self'` with no nonce silently
// blocks Next.js's own required inline hydration script).
const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
];

const nextConfig: NextConfig = {
  transpilePackages: ["@mehndiverse/contracts", "@mehndiverse/design-tokens"],
  // Self-contained `.next/standalone` output — see Dockerfile and
  // docs/deployment.md#api-web-admin.
  output: "standalone",
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;

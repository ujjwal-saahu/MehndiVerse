import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { middleware } from "./middleware";

describe("middleware", () => {
  it("allows unauthenticated access to non-protected routes", () => {
    const request = new NextRequest("http://localhost/login");
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects to /login when the protected route has no session cookie", () => {
    const request = new NextRequest("http://localhost/account");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to a protected route when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/account", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /discover", () => {
    const request = new NextRequest("http://localhost/discover");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("redirects unauthenticated visitors away from a shared design URL", () => {
    const request = new NextRequest("http://localhost/designs/some-design-id");
    const response = middleware(request);
    expect(response.status).toBe(307);
    const location = response.headers.get("location");
    expect(location).toContain("/login");
    expect(location).toContain("from=%2Fdesigns%2Fsome-design-id");
  });

  it("allows access to a shared design URL when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/designs/some-design-id", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /search", () => {
    const request = new NextRequest("http://localhost/search");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to /search when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/search", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /collections", () => {
    const request = new NextRequest("http://localhost/collections");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to /collections when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/collections", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /saved", () => {
    const request = new NextRequest("http://localhost/saved");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to /saved when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/saved", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /artist", () => {
    const request = new NextRequest("http://localhost/artist/onboarding");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to /artist when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/artist/onboarding", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /admin", () => {
    const request = new NextRequest("http://localhost/admin/artists");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to /admin when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/admin/artists", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects unauthenticated visitors away from /artists", () => {
    const request = new NextRequest("http://localhost/artists");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access to /artists when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/artists", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("rejects a cross-origin POST to /api/* by Origin header", () => {
    const request = new NextRequest("http://localhost/api/profile", {
      method: "POST",
      headers: { origin: "https://evil.example" },
    });
    const response = middleware(request);
    expect(response.status).toBe(403);
  });

  it("rejects a cross-origin POST to /api/* by Referer when Origin is absent", () => {
    const request = new NextRequest("http://localhost/api/profile", {
      method: "POST",
      headers: { referer: "https://evil.example/attack" },
    });
    const response = middleware(request);
    expect(response.status).toBe(403);
  });

  it("allows a same-origin POST to /api/*", () => {
    const request = new NextRequest("http://localhost/api/profile", {
      method: "POST",
      headers: { origin: "http://localhost" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("allows a GET to /api/* regardless of Origin", () => {
    const request = new NextRequest("http://localhost/api/profile", {
      method: "GET",
      headers: { origin: "https://evil.example" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });
});

import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { middleware } from "./middleware";

describe("admin middleware", () => {
  it("allows unauthenticated access to /login", () => {
    const request = new NextRequest("http://localhost/login");
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("redirects to /login when there is no session cookie", () => {
    const request = new NextRequest("http://localhost/dashboard");
    const response = middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/login");
  });

  it("allows access when the session cookie is present", () => {
    const request = new NextRequest("http://localhost/dashboard", {
      headers: { cookie: "mv_admin_access_token=at-123" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });

  it("rejects a cross-origin POST to /api/* by Origin header", () => {
    const request = new NextRequest("http://localhost/api/admin/users/1", {
      method: "POST",
      headers: { origin: "https://evil.example" },
    });
    const response = middleware(request);
    expect(response.status).toBe(403);
  });

  it("allows a same-origin POST to /api/*", () => {
    const request = new NextRequest("http://localhost/api/auth/login", {
      method: "POST",
      headers: { origin: "http://localhost" },
    });
    const response = middleware(request);
    expect(response.status).toBe(200);
  });
});

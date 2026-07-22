import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

function requestWithCookie(cookie?: string): NextRequest {
  return new NextRequest("http://localhost/api/auth/me", {
    headers: cookie ? { cookie } : {},
  });
}

describe("GET /api/auth/me", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(requestWithCookie());
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's user payload", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "u1",
          email: "person@example.com",
          role: "customer",
          status: "active",
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(requestWithCookie("mv_access_token=at-123"));

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
    const body = (await response.json()) as { email: string };
    expect(body.email).toBe("person@example.com");
  });
});

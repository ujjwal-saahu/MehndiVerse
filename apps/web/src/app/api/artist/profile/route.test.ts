import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, PATCH } from "./route";

function requestWithCookie(method: string, cookie?: string, body?: unknown): NextRequest {
  return new NextRequest("http://localhost/api/artist/profile", {
    method,
    headers: cookie ? { cookie } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

describe("GET /api/artist/profile", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(requestWithCookie("GET"));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's profile payload", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ verification_status: "draft" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(requestWithCookie("GET", "mv_access_token=at-123"));

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("PATCH /api/artist/profile", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await PATCH(requestWithCookie("PATCH", undefined, { bio: "Hi" }));
    expect(response.status).toBe(401);
  });

  it("forwards the request body to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ verification_status: "draft" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await PATCH(
      requestWithCookie("PATCH", "mv_access_token=at-123", { professional_name: "Priya" }),
    );

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(JSON.stringify({ professional_name: "Priya" }));
  });

  it("propagates a validation error from the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Country must be a 2-letter code." }), {
          status: 422,
        }),
      ),
    );

    const response = await PATCH(
      requestWithCookie("PATCH", "mv_access_token=at-123", { country: "India" }),
    );

    expect(response.status).toBe(422);
  });
});

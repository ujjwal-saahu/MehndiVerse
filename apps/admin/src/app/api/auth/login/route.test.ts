import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

function jsonRequest(body: unknown): Request {
  return new Request("http://localhost/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function tokenResponse() {
  return new Response(
    JSON.stringify({ access_token: "at-123", refresh_token: "rt-123", expires_in: 3600 }),
    { status: 200 },
  );
}

describe("POST /api/auth/login (admin)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects a customer account even with correct credentials", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(tokenResponse())
      .mockResolvedValueOnce(new Response(JSON.stringify({ role: "customer" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      jsonRequest({ email: "customer@example.com", password: "correct-horse" }),
    );

    expect(response.status).toBe(403);
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("grants a session cookie for a moderator account", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(tokenResponse())
      .mockResolvedValueOnce(new Response(JSON.stringify({ role: "moderator" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      jsonRequest({ email: "mod@example.com", password: "correct-horse" }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie") ?? "").toContain("mv_admin_access_token=at-123");
  });
});

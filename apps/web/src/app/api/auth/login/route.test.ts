import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

function jsonRequest(body: unknown): Request {
  return new Request("http://localhost/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

describe("POST /api/auth/login", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects an invalid payload before calling the backend", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(jsonRequest({ email: "not-an-email", password: "" }));

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("sets httpOnly session cookies on a successful login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: "at-123",
            refresh_token: "rt-123",
            expires_in: 3600,
          }),
          { status: 200 },
        ),
      ),
    );

    const response = await POST(
      jsonRequest({ email: "person@example.com", password: "correct-horse" }),
    );

    expect(response.status).toBe(200);
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain("mv_access_token=at-123");
    expect(setCookie.toLowerCase()).toContain("httponly");
  });

  it("propagates the backend's error message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { message: "Invalid email or password." } }), {
          status: 401,
        }),
      ),
    );

    const response = await POST(jsonRequest({ email: "person@example.com", password: "wrong" }));

    expect(response.status).toBe(401);
    const body = (await response.json()) as { message: string };
    expect(body.message).toBe("Invalid email or password.");
  });
});

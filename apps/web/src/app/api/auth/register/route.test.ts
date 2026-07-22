import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

function jsonRequest(body: unknown): Request {
  return new Request("http://localhost/api/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

describe("POST /api/auth/register", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects registration when terms_accepted is missing, without calling the backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      jsonRequest({ email: "new@example.com", password: "supersecret123" }),
    );

    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects registration when terms_accepted is false", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      jsonRequest({
        email: "new@example.com",
        password: "supersecret123",
        terms_accepted: false,
      }),
    );

    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards a valid registration (with terms accepted) to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          message: "Registration successful. Please check your email to verify your account.",
          session: null,
        }),
        { status: 201 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      jsonRequest({
        email: "new@example.com",
        password: "supersecret123",
        terms_accepted: true,
      }),
    );

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.needsVerification).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/comments/[id]/report", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/comments/c1/report", { method: "POST" }),
      { params: Promise.resolve({ id: "c1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the report reason and status", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "r1", status: "pending" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/comments/c1/report", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ reason: "Spam" }),
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ reason: "Spam" });
  });

  it("surfaces a 409 from the backend when a pending report already exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "conflict", message: "Already reported" } }), {
          status: 409,
        }),
      ),
    );

    const response = await POST(
      new NextRequest("http://localhost/api/comments/c1/report", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ reason: "Spam again" }),
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(409);
  });
});

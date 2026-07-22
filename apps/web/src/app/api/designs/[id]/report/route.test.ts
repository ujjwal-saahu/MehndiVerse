import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/designs/[id]/report", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/report", { method: "POST" }),
      { params: Promise.resolve({ id: "d1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "r1", status: "pending" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/report", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ reason: "Stolen art" }),
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(201);
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/d1/report");
  });
});

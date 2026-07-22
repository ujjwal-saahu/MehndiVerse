import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/admin/reports/[id]/[action]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/admin/reports/r1/resolve", { method: "POST" }),
      { params: Promise.resolve({ id: "r1", action: "resolve" }) },
    );
    expect(response.status).toBe(401);
  });

  it("rejects an action not on the allow-list", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/admin/reports/r1/delete-everything", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "r1", action: "delete-everything" }) },
    );
    expect(response.status).toBe(404);
  });

  it("forwards resolve to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "r1", status: "resolved" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/admin/reports/r1/resolve", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ resolution_notes: "Looked into it" }),
      }),
      { params: Promise.resolve({ id: "r1", action: "resolve" }) },
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/admin/reports/r1/resolve");
  });

  it("forwards dismiss to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "r1", status: "dismissed" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/admin/reports/r1/dismiss", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ resolution_notes: null }),
      }),
      { params: Promise.resolve({ id: "r1", action: "dismiss" }) },
    );

    expect(response.status).toBe(200);
  });
});

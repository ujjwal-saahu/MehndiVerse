import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PATCH } from "./route";

describe("PATCH /api/admin/artists/[id]/documents/[documentId]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/admin/artists/a1/documents/d1", {
      method: "PATCH",
      body: JSON.stringify({ status: "approved" }),
    });
    const response = await PATCH(request, {
      params: Promise.resolve({ id: "a1", documentId: "d1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the review decision to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "d1", status: "rejected" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/admin/artists/a1/documents/d1", {
      method: "PATCH",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ status: "rejected", rejection_reason: "Blurry photo" }),
    });
    const response = await PATCH(request, {
      params: Promise.resolve({ id: "a1", documentId: "d1" }),
    });

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/admin/artists/a1/documents/d1");
    expect(init.body).toBe(
      JSON.stringify({ status: "rejected", rejection_reason: "Blurry photo" }),
    );
  });
});

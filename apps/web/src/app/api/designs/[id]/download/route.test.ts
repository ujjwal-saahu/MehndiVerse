import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/designs/[id]/download", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/designs/d1/download", {
      method: "POST",
    });
    const response = await POST(request, { params: Promise.resolve({ id: "d1" }) });
    expect(response.status).toBe(401);
  });

  it("propagates a 403 when the quota is exhausted", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ error: { message: "Quota exhausted." } }), { status: 403 }),
        ),
    );

    const request = new NextRequest("http://localhost/api/designs/d1/download", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await POST(request, { params: Promise.resolve({ id: "d1" }) });

    expect(response.status).toBe(403);
    const body = await response.json();
    expect(body.message).toBe("Quota exhausted.");
  });
});

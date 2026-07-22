import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

function requestWithCookie(cookie?: string, body?: unknown): NextRequest {
  return new NextRequest("http://localhost/api/admin/artists/a1/approve", {
    method: "POST",
    headers: cookie ? { cookie } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

describe("POST /api/admin/artists/[id]/[action]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(requestWithCookie(), {
      params: Promise.resolve({ id: "a1", action: "approve" }),
    });
    expect(response.status).toBe(401);
  });

  it("rejects an action outside the allow-list without ever calling fetch", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(requestWithCookie("mv_access_token=at-123"), {
      params: Promise.resolve({ id: "a1", action: "delete-everything" }),
    });

    expect(response.status).toBe(404);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each(["start-review", "approve", "reject", "request-more-information", "suspend"])(
    "forwards the allow-listed action '%s' to the matching backend path",
    async (action) => {
      const fetchSpy = vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ verification_status: "under_review" }), { status: 200 }),
        );
      vi.stubGlobal("fetch", fetchSpy);

      const response = await POST(requestWithCookie("mv_access_token=at-123", { reason: "why" }), {
        params: Promise.resolve({ id: "a1", action }),
      });

      expect(response.status).toBe(200);
      const [url] = fetchSpy.mock.calls[0] as [string];
      expect(url).toContain(`/admin/artists/a1/${action}`);
    },
  );

  it("propagates a 403 when the backend blocks self-approval", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "You cannot review your own artist application." }), {
          status: 403,
        }),
      ),
    );

    const response = await POST(requestWithCookie("mv_access_token=at-123"), {
      params: Promise.resolve({ id: "a1", action: "approve" }),
    });

    expect(response.status).toBe(403);
  });
});

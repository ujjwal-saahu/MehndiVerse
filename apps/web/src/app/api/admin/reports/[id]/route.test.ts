import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/admin/reports/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/admin/reports/r1"), {
      params: Promise.resolve({ id: "r1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards to the backend, including the entity snapshot", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ id: "r1", entity_snapshot: { body: "Nasty comment" } }), {
          status: 200,
        }),
      ),
    );

    const response = await GET(
      new NextRequest("http://localhost/api/admin/reports/r1", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "r1" }) },
    );

    expect(response.status).toBe(200);
    const body = (await response.json()) as { entity_snapshot: { body: string } };
    expect(body.entity_snapshot.body).toBe("Nasty comment");
  });
});

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/users/[id]/report", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/users/u1/report", { method: "POST" }),
      { params: Promise.resolve({ id: "u1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards to the backend and surfaces a 422 for self-reports", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "unprocessable", message: "You cannot report yourself." },
          }),
          { status: 422 },
        ),
      ),
    );

    const response = await POST(
      new NextRequest("http://localhost/api/users/u1/report", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ reason: "self report" }),
      }),
      { params: Promise.resolve({ id: "u1" }) },
    );

    expect(response.status).toBe(422);
  });
});

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

function formDataRequest(fields: Record<string, string | Blob>): NextRequest {
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    formData.set(key, value);
  }
  return new NextRequest("http://localhost/api/previews", {
    method: "POST",
    body: formData,
    headers: { cookie: "mv_access_token=at-123" },
  });
}

describe("POST /api/previews", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const formData = new FormData();
    formData.set("file", new Blob(["x"]), "photo.png");
    const request = new NextRequest("http://localhost/api/previews", {
      method: "POST",
      body: formData,
    });
    const response = await POST(request);
    expect(response.status).toBe(401);
  });

  it("returns 422 when no file is provided", async () => {
    const request = formDataRequest({ design_id: "d1" });
    const response = await POST(request);
    expect(response.status).toBe(422);
  });

  it("forwards the file and fields to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "p1" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = formDataRequest({
      file: new Blob(["x"], { type: "image/png" }),
      design_id: "d1",
      overlay_transform: JSON.stringify({ x: 0.5 }),
    });
    const response = await POST(request);

    expect(response.status).toBe(201);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/previews");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
    const forwardedBody = init.body as FormData;
    expect(forwardedBody.get("design_id")).toBe("d1");
  });
});

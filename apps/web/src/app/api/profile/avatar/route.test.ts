import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

function requestWithFile(cookie: string | null, file?: Blob): NextRequest {
  const formData = new FormData();
  if (file) formData.set("file", file, "avatar.png");
  return new NextRequest("http://localhost/api/profile/avatar", {
    method: "POST",
    headers: cookie ? { cookie } : {},
    body: formData,
  });
}

describe("POST /api/profile/avatar", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(requestWithFile(null, new Blob(["fake"], { type: "image/png" })));
    expect(response.status).toBe(401);
  });

  it("rejects a request with no file", async () => {
    const response = await POST(requestWithFile("mv_access_token=at-123"));
    expect(response.status).toBe(422);
  });

  it("forwards the file to the backend and returns the avatar URL", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ avatar_url: "https://storage.test/avatars/u1/avatar.png" }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      requestWithFile("mv_access_token=at-123", new Blob(["fake"], { type: "image/png" })),
    );

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/users/me/avatar");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
    expect(init.body).toBeInstanceOf(FormData);
    const body = (await response.json()) as { avatar_url: string };
    expect(body.avatar_url).toBe("https://storage.test/avatars/u1/avatar.png");
  });
});

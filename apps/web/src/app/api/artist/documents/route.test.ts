import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/artist/documents", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/artist/documents");
    const response = await GET(request);
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's document list", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/artist/documents", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("POST /api/artist/documents", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const formData = new FormData();
    formData.set("file", new Blob(["%PDF-1.4"], { type: "application/pdf" }), "id.pdf");
    formData.set("document_type", "id_proof");
    const request = new NextRequest("http://localhost/api/artist/documents", {
      method: "POST",
      body: formData,
    });
    const response = await POST(request);
    expect(response.status).toBe(401);
  });

  it("returns 422 when no file is provided", async () => {
    const formData = new FormData();
    formData.set("document_type", "id_proof");
    const request = new NextRequest("http://localhost/api/artist/documents", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: formData,
    });
    const response = await POST(request);
    expect(response.status).toBe(422);
  });

  it("returns 422 when document_type is missing", async () => {
    const formData = new FormData();
    formData.set("file", new Blob(["%PDF-1.4"], { type: "application/pdf" }), "id.pdf");
    const request = new NextRequest("http://localhost/api/artist/documents", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: formData,
    });
    const response = await POST(request);
    expect(response.status).toBe(422);
  });

  it("forwards a well-formed upload to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "doc-1", status: "pending" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const formData = new FormData();
    formData.set("file", new Blob(["%PDF-1.4"], { type: "application/pdf" }), "id.pdf");
    formData.set("document_type", "id_proof");
    const request = new NextRequest("http://localhost/api/artist/documents", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: formData,
    });

    const response = await POST(request);

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

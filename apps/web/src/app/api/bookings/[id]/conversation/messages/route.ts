import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendBaseUrl, backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const query = request.nextUrl.search;
  const backendResponse = await backendFetch(`/bookings/${id}/conversation/messages${query}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

/** Forwards as multipart/form-data — the backend accepts an optional text
 * `body` field and an optional `file` field on the same endpoint. */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const incoming = await request.formData().catch(() => null);
  if (incoming === null) {
    return NextResponse.json({ message: "Invalid form data." }, { status: 422 });
  }

  const outgoing = new FormData();
  const body = incoming.get("body");
  if (typeof body === "string" && body.length > 0) {
    outgoing.set("body", body);
  }
  const file = incoming.get("file");
  if (file instanceof Blob) {
    outgoing.set("file", file, file instanceof File ? file.name : "image");
  }

  const { id } = await params;
  const backendResponse = await fetch(
    `${backendBaseUrl()}/api/v1/bookings/${id}/conversation/messages`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: outgoing,
      cache: "no-store",
    },
  );

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json(), { status: backendResponse.status });
}

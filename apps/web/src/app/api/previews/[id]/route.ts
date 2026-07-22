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
  const backendResponse = await backendFetch(`/previews/${id}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

/** Multipart pass-through, all fields optional — mirrors
 * src/app/api/previews/route.ts. */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const incoming = await request.formData().catch(() => null);
  const outgoing = new FormData();
  const file = incoming?.get("file");
  if (file instanceof Blob) outgoing.set("file", file, file instanceof File ? file.name : "photo");
  const designId = incoming?.get("design_id");
  if (typeof designId === "string") outgoing.set("design_id", designId);
  const overlayTransform = incoming?.get("overlay_transform");
  if (typeof overlayTransform === "string") outgoing.set("overlay_transform", overlayTransform);

  const backendResponse = await fetch(`${backendBaseUrl()}/api/v1/previews/${id}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: outgoing,
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const backendResponse = await backendFetch(`/previews/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return new NextResponse(null, { status: 204 });
}

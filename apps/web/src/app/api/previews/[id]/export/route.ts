import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendBaseUrl, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** The composited (photo + overlay) image is rendered entirely client-side
 * — this route just forwards those already-flattened bytes. See
 * docs/hand-foot-preview.md#export. */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const incoming = await request.formData().catch(() => null);
  const file = incoming?.get("file");
  if (!(file instanceof Blob)) {
    return NextResponse.json({ message: "No file provided." }, { status: 422 });
  }
  const outgoing = new FormData();
  outgoing.set("file", file, "export.png");

  const backendResponse = await fetch(`${backendBaseUrl()}/api/v1/previews/${id}/export`, {
    method: "POST",
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

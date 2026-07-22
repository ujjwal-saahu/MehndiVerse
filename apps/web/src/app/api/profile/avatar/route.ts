import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendBaseUrl, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Forwards the uploaded file to the backend as multipart/form-data. This
 * route deliberately does NOT go through backendFetch() (which forces a JSON
 * Content-Type) — the browser-supplied file is re-packaged into a fresh
 * FormData so `fetch` computes its own multipart boundary header. The
 * backend re-validates type/size and strips metadata before storing anything
 * (see docs/profile-and-privacy.md#avatar-uploads); this route is just a
 * pass-through that keeps the browser from needing the backend's URL or a
 * raw access token. */
export async function POST(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const incoming = await request.formData().catch(() => null);
  const file = incoming?.get("file");
  if (!(file instanceof Blob)) {
    return NextResponse.json({ message: "No file provided." }, { status: 422 });
  }

  const outgoing = new FormData();
  outgoing.set("file", file, file instanceof File ? file.name : "avatar");

  const backendResponse = await fetch(`${backendBaseUrl()}/api/v1/users/me/avatar`, {
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

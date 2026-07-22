import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendBaseUrl, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Forwards the uploaded file to the backend as multipart/form-data — mirrors
 * src/app/api/profile/avatar/route.ts's pass-through pattern. */
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
  outgoing.set("file", file, file instanceof File ? file.name : "cover-image");

  const backendResponse = await fetch(`${backendBaseUrl()}/api/v1/artist/profile/cover-image`, {
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

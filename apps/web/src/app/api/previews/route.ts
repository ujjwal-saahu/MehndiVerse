import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendBaseUrl, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Multipart pass-through — mirrors src/app/api/profile/avatar/route.ts.
 * The hand/foot photo only ever reaches this route (and the backend) once
 * the user explicitly saves a project; see
 * docs/hand-foot-preview.md#do-not-upload-private-photos-unless-required. */
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
  outgoing.set("file", file, file instanceof File ? file.name : "photo");
  const designId = incoming?.get("design_id");
  if (typeof designId === "string") outgoing.set("design_id", designId);
  const overlayTransform = incoming?.get("overlay_transform");
  if (typeof overlayTransform === "string") outgoing.set("overlay_transform", overlayTransform);

  const backendResponse = await fetch(`${backendBaseUrl()}/api/v1/previews`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: outgoing,
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json(), { status: backendResponse.status });
}

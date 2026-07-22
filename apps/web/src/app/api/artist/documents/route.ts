import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendBaseUrl, backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const backendResponse = await backendFetch("/artist/documents", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

/** Forwards the uploaded file + document_type to the backend as
 * multipart/form-data — mirrors src/app/api/profile/avatar/route.ts. */
export async function POST(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const incoming = await request.formData().catch(() => null);
  const file = incoming?.get("file");
  const documentType = incoming?.get("document_type");
  if (!(file instanceof Blob) || typeof documentType !== "string") {
    return NextResponse.json(
      { message: "A file and document_type are required." },
      { status: 422 },
    );
  }

  const outgoing = new FormData();
  outgoing.set("file", file, file instanceof File ? file.name : "document");
  outgoing.set("document_type", documentType);

  const backendResponse = await fetch(`${backendBaseUrl()}/api/v1/artist/documents`, {
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

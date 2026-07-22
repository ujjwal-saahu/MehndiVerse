import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const query = request.nextUrl.search;
  const backendResponse = await backendFetch(`/artists/${id}/availability/slots${query}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Proxies to the backend's cursor-paginated `/designs/published` — see
 * docs/design-gallery.md#cursor-based-pagination. Query params are passed
 * through as-is (category_id, difficulty_level, body_placement, sort,
 * cursor, limit). */
export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const query = request.nextUrl.searchParams.toString();
  const backendResponse = await backendFetch(`/designs/published${query ? `?${query}` : ""}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  const response = NextResponse.json(await backendResponse.json());
  const cacheControl = backendResponse.headers.get("cache-control");
  if (cacheControl) response.headers.set("cache-control", cacheControl);
  return response;
}

export async function POST(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const body = await request.text();
  const backendResponse = await backendFetch("/designs", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body,
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json(), { status: backendResponse.status });
}

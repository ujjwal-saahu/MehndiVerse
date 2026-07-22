import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Proxies `/categories` — this one isn't under the backend's `/admin/*`
 * prefix (customers can read it too), so it isn't covered by the generic
 * `/api/admin/[...path]` proxy. See docs/admin-dashboard.md#category-
 * management. */
export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const query = request.nextUrl.search;
  const backendResponse = await backendFetch(`/categories${query}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }
  return NextResponse.json(await backendResponse.json());
}

export async function POST(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const body = await request.text();
  const backendResponse = await backendFetch("/categories", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body,
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }
  return NextResponse.json(await backendResponse.json(), { status: 201 });
}

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Proxies to the backend's `/designs/search/suggestions` — see
 * docs/design-search.md#search-suggestions. */
export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const query = request.nextUrl.searchParams.toString();
  const backendResponse = await backendFetch(
    `/designs/search/suggestions${query ? `?${query}` : ""}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

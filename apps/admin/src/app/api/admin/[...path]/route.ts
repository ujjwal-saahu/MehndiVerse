import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** A single generic proxy for every `/admin/*` backend route, rather than
 * one route.ts per module (19 modules, most with list+action endpoints —
 * see docs/admin-dashboard.md#generic-admin-proxy). Every backend route
 * under this prefix already requires a staff role via `require_roles()`,
 * so there's no per-route authorization logic this proxy would need to
 * duplicate — it only has to attach the caller's bearer token and forward
 * the method/query/body, exactly like every other proxy route in this
 * codebase does for one specific path.
 */
async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const targetPath = `/admin/${path.join("/")}`;
  const query = request.nextUrl.search;
  const hasBody =
    request.method !== "GET" && request.method !== "DELETE" && request.method !== "HEAD";

  const backendResponse = await backendFetch(`${targetPath}${query}`, {
    method: request.method,
    headers: { Authorization: `Bearer ${accessToken}` },
    body: hasBody ? await request.text() : undefined,
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }
  if (backendResponse.status === 204) {
    return new NextResponse(null, { status: 204 });
  }
  return NextResponse.json(await backendResponse.json(), { status: backendResponse.status });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function PATCH(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function PUT(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function DELETE(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

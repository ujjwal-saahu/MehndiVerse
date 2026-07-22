import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** One dynamic route proxies all five verification-transition actions
 * (matching app/api/routes/admin_artist_verification.py 1:1) rather than
 * five near-identical route files — the allow-list below is what keeps this
 * safe: only these exact backend paths can ever be reached. */
const ALLOWED_ACTIONS = new Set([
  "start-review",
  "approve",
  "reject",
  "request-more-information",
  "suspend",
]);

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; action: string }> },
) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { id, action } = await params;
  if (!ALLOWED_ACTIONS.has(action)) {
    return NextResponse.json({ message: "Unknown action." }, { status: 404 });
  }

  const body = await request.text();
  const backendResponse = await backendFetch(`/admin/artists/${id}/${action}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: body || undefined,
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

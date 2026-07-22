import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

/** Mirrors app/api/routes/admin_moderation.py's two report actions —
 * see src/app/api/admin/artists/[id]/[action]/route.ts for the identical
 * allow-list pattern this is copied from. */
const ALLOWED_ACTIONS = new Set(["resolve", "dismiss"]);

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
  const backendResponse = await backendFetch(`/admin/reports/${id}/${action}`, {
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

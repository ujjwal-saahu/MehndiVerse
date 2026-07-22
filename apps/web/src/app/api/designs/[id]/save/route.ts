import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

async function proxy(request: NextRequest, id: string, method: "POST" | "DELETE") {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const backendResponse = await backendFetch(`/designs/${id}/save`, {
    method,
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxy(request, id, "POST");
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxy(request, id, "DELETE");
}

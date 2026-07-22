import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE, clearSessionCookies } from "@/lib/session-cookies";

export async function POST(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;

  if (accessToken) {
    await backendFetch("/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
    }).catch(() => undefined); // best-effort — clear the local session regardless
  }

  const response = NextResponse.json({ message: "Logged out." });
  clearSessionCookies(response);
  return response;
}

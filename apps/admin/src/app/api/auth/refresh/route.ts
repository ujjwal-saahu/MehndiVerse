import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import {
  clearSessionCookies,
  REFRESH_TOKEN_COOKIE,
  setSessionCookies,
} from "@/lib/session-cookies";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;
  if (!refreshToken) {
    return NextResponse.json({ message: "No session to refresh." }, { status: 401 });
  }

  const backendResponse = await backendFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    const response = NextResponse.json({ message }, { status: backendResponse.status });
    clearSessionCookies(response);
    return response;
  }

  const session = (await backendResponse.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };

  const response = NextResponse.json({ message: "Session refreshed." });
  setSessionCookies(response, {
    accessToken: session.access_token,
    refreshToken: session.refresh_token,
    expiresIn: session.expires_in,
  });
  return response;
}

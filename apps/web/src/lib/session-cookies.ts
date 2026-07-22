import type { NextResponse } from "next/server";

export const ACCESS_TOKEN_COOKIE = "mv_access_token";
export const REFRESH_TOKEN_COOKIE = "mv_refresh_token";

const THIRTY_DAYS_SECONDS = 60 * 60 * 24 * 30;

/** httpOnly + Secure(prod) + SameSite=Lax — never readable by client-side JS,
 * so an XSS bug can't exfiltrate the session token. See
 * docs/authentication.md#7. */
export function setSessionCookies(
  response: NextResponse,
  params: { accessToken: string; refreshToken: string; expiresIn: number },
): void {
  const secure = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_TOKEN_COOKIE, params.accessToken, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: params.expiresIn,
  });
  response.cookies.set(REFRESH_TOKEN_COOKIE, params.refreshToken, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: THIRTY_DAYS_SECONDS,
  });
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.delete(ACCESS_TOKEN_COOKIE);
  response.cookies.delete(REFRESH_TOKEN_COOKIE);
}

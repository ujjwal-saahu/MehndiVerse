import { NextResponse } from "next/server";
import { z } from "zod";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { setSessionCookies } from "@/lib/session-cookies";

const STAFF_ROLES = new Set(["moderator", "admin", "super_admin"]);

const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(1),
});

export async function POST(request: Request) {
  const parsed = loginSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ message: "Invalid email or password." }, { status: 422 });
  }

  const backendResponse = await backendFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify(parsed.data),
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  const session = (await backendResponse.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };

  // The admin app is staff-only (see docs/user-roles-and-permissions.md —
  // Moderator/Administrator/Super Administrator are not self-service
  // signups). Verify the role server-side via /auth/me *before* granting a
  // session cookie here — never trust anything the client could have sent.
  const meResponse = await backendFetch("/auth/me", {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  if (!meResponse.ok) {
    return NextResponse.json({ message: "Unable to verify account." }, { status: 401 });
  }
  const me = (await meResponse.json()) as { role: string };
  if (!STAFF_ROLES.has(me.role)) {
    return NextResponse.json(
      { message: "This account does not have access to the admin dashboard." },
      { status: 403 },
    );
  }

  const response = NextResponse.json({ message: "Logged in.", role: me.role });
  setSessionCookies(response, {
    accessToken: session.access_token,
    refreshToken: session.refresh_token,
    expiresIn: session.expires_in,
  });
  return response;
}

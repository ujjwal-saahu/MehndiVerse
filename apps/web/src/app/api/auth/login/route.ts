import { NextResponse } from "next/server";
import { z } from "zod";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { setSessionCookies } from "@/lib/session-cookies";

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

  const response = NextResponse.json({ message: "Logged in." });
  setSessionCookies(response, {
    accessToken: session.access_token,
    refreshToken: session.refresh_token,
    expiresIn: session.expires_in,
  });
  return response;
}

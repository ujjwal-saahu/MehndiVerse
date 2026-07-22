import { NextResponse } from "next/server";
import { z } from "zod";

import { backendFetch, extractErrorMessage } from "@/lib/backend";
import { setSessionCookies } from "@/lib/session-cookies";

// No `role` field — registration always creates a customer, enforced by the
// backend regardless of what a client sends. See docs/authentication.md#3.
const registerSchema = z.object({
  email: z.email(),
  password: z.string().min(8).max(72),
  terms_accepted: z.literal(true),
});

export async function POST(request: Request) {
  const parsed = registerSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json(
      {
        message:
          "Please provide a valid email, a password of at least 8 characters, and accept the Terms of Service and Privacy Policy.",
      },
      { status: 422 },
    );
  }

  const backendResponse = await backendFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(parsed.data),
  });

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  const body = (await backendResponse.json()) as {
    message: string;
    session: { access_token: string; refresh_token: string; expires_in: number } | null;
  };

  if (!body.session) {
    return NextResponse.json({ message: body.message, needsVerification: true });
  }

  const response = NextResponse.json({ message: body.message, needsVerification: false });
  setSessionCookies(response, {
    accessToken: body.session.access_token,
    refreshToken: body.session.refresh_token,
    expiresIn: body.session.expires_in,
  });
  return response;
}

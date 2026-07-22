import { NextResponse } from "next/server";
import { z } from "zod";

import { backendFetch } from "@/lib/backend";

const schema = z.object({ email: z.email() });

export async function POST(request: Request) {
  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ message: "Please provide a valid email." }, { status: 422 });
  }

  // Always return the same generic response regardless of backend outcome —
  // never reveal whether an email is registered.
  await backendFetch("/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify(parsed.data),
  }).catch(() => undefined);

  return NextResponse.json({
    message: "If an account exists for this email, a password reset link has been sent.",
  });
}

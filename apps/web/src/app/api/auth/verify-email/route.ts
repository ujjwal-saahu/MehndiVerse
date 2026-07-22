import { NextResponse } from "next/server";
import { z } from "zod";

import { backendFetch } from "@/lib/backend";

const schema = z.object({ email: z.email() });

export async function POST(request: Request) {
  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ message: "Please provide a valid email." }, { status: 422 });
  }

  await backendFetch("/auth/verify-email/resend", {
    method: "POST",
    body: JSON.stringify(parsed.data),
  }).catch(() => undefined);

  return NextResponse.json({
    message: "If an account exists for this email, a verification email has been sent.",
  });
}

import { NextResponse } from "next/server";

import { backendFetch, extractErrorMessage } from "@/lib/backend";

/** Public — no session required, mirrors the backend's `GET
 * /subscription-plans` (see docs/subscriptions-and-entitlements.md). */
export async function GET() {
  const backendResponse = await backendFetch("/subscriptions/plans");

  if (!backendResponse.ok) {
    const message = await extractErrorMessage(backendResponse);
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  return NextResponse.json(await backendResponse.json());
}

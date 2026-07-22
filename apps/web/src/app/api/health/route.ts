import { NextResponse } from "next/server";
import type { ServiceHealth } from "@mehndiverse/contracts";

export function GET() {
  const body: ServiceHealth = { status: "ok", service: "web" };
  return NextResponse.json(body);
}

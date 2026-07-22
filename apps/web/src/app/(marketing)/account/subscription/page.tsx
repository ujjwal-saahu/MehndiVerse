import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { SubscriptionView } from "./subscription-view";

export default async function SubscriptionPage() {
  const hasSession = (await cookies()).has(ACCESS_TOKEN_COOKIE);
  if (!hasSession) {
    redirect("/login");
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">My subscription</h1>
      <SubscriptionView />
    </div>
  );
}

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { VerificationQueueView } from "./verification-queue-view";

const STAFF_ROLES = new Set(["moderator", "admin", "super_admin"]);

export default async function AdminArtistsQueuePage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const meResponse = await backendFetch("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!meResponse.ok) {
    redirect("/login");
  }
  const me = (await meResponse.json()) as { role: string };
  if (!STAFF_ROLES.has(me.role)) {
    redirect("/account");
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        Artist verification queue
      </h1>
      <div className="mt-6">
        <VerificationQueueView />
      </div>
    </div>
  );
}

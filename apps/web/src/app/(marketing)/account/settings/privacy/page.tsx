import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { BlockedUserData, PreferencesData } from "@/lib/profile-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { PrivacySettingsForm } from "./privacy-settings-form";

export default async function PrivacySettingsPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const [preferencesResponse, blocksResponse] = await Promise.all([
    backendFetch("/users/me/preferences", { headers: { Authorization: `Bearer ${accessToken}` } }),
    backendFetch("/users/me/blocks", { headers: { Authorization: `Bearer ${accessToken}` } }),
  ]);
  if (!preferencesResponse.ok) {
    redirect("/login");
  }

  const preferences = (await preferencesResponse.json()) as PreferencesData;
  const blockedUsers = blocksResponse.ok
    ? ((await blocksResponse.json()) as BlockedUserData[])
    : [];

  return (
    <div className="mx-auto max-w-xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Privacy</h1>
      <div className="mt-6">
        <PrivacySettingsForm preferences={preferences} initialBlockedUsers={blockedUsers} />
      </div>
    </div>
  );
}

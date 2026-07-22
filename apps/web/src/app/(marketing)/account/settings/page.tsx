import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { PreferencesData, ProfileData } from "@/lib/profile-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { SettingsForm } from "./settings-form";

export default async function AccountSettingsPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const [profileResponse, preferencesResponse] = await Promise.all([
    backendFetch("/users/me/profile", { headers: { Authorization: `Bearer ${accessToken}` } }),
    backendFetch("/users/me/preferences", { headers: { Authorization: `Bearer ${accessToken}` } }),
  ]);
  if (!profileResponse.ok || !preferencesResponse.ok) {
    redirect("/login");
  }

  const profile = (await profileResponse.json()) as ProfileData;
  const preferences = (await preferencesResponse.json()) as PreferencesData;

  return (
    <div className="mx-auto max-w-xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Settings</h1>
      <div className="mt-6">
        <SettingsForm profile={profile} preferences={preferences} />
      </div>
    </div>
  );
}

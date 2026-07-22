import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ProfileData } from "@/lib/profile-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { EditProfileForm } from "./edit-profile-form";

export default async function EditProfilePage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch("/users/me/profile", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    redirect("/login");
  }
  const profile = (await response.json()) as ProfileData;

  return (
    <div className="mx-auto max-w-xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Edit profile</h1>
      <div className="mt-6">
        <EditProfileForm profile={profile} />
      </div>
    </div>
  );
}

import Image from "next/image";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ProfileData } from "@/lib/profile-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { AccountActions } from "./account-actions";

interface CurrentUser {
  id: string;
  email: string;
  role: string;
  status: string;
}

export default async function AccountPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const [userResponse, profileResponse] = await Promise.all([
    backendFetch("/auth/me", { headers: { Authorization: `Bearer ${accessToken}` } }),
    backendFetch("/users/me/profile", { headers: { Authorization: `Bearer ${accessToken}` } }),
  ]);

  if (!userResponse.ok) {
    redirect("/login");
  }

  const user = (await userResponse.json()) as CurrentUser;
  const profile = profileResponse.ok ? ((await profileResponse.json()) as ProfileData) : null;
  const location = [profile?.city, profile?.country].filter(Boolean).join(", ");

  return (
    <div className="mx-auto max-w-xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Account</h1>
      <div className="mt-6 rounded-xl border border-border bg-surface p-6">
        <div className="flex items-center gap-4">
          <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full bg-surface-variant">
            {profile?.avatar_url ? (
              <Image src={profile.avatar_url} alt="" fill sizes="64px" className="object-cover" />
            ) : null}
          </div>
          <div>
            <p className="font-medium text-text-primary">{profile?.display_name ?? user.email}</p>
            <p className="text-sm text-text-secondary">{user.email}</p>
          </div>
        </div>
        {profile?.bio ? <p className="mt-4 text-text-primary">{profile.bio}</p> : null}
        {location ? <p className="mt-1 text-sm text-text-secondary">{location}</p> : null}
        <p className="mt-1 text-sm text-text-secondary">Role: {user.role}</p>
      </div>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Link
          href="/account/edit"
          className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Edit profile
        </Link>
        <Link
          href="/account/settings"
          className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Settings
        </Link>
        <Link
          href="/account/subscription"
          className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          My subscription
        </Link>
        <Link
          href="/bookings"
          className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          My bookings
        </Link>
        <Link
          href="/messages"
          className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Messages
        </Link>
        <Link
          href="/notifications"
          className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Notifications
        </Link>
      </div>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        {user.role === "customer" || user.role === "premium_customer" ? (
          <Link
            href="/artist/onboarding"
            className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Become an artist
          </Link>
        ) : null}
        {user.role === "artist" || user.role === "verified_artist" ? (
          <>
            <Link
              href="/artist/verification-status"
              className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Artist verification status
            </Link>
            <Link
              href="/artist/portfolio"
              className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              My portfolio
            </Link>
            <Link
              href="/artist/services"
              className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              My services
            </Link>
            <Link
              href="/artist/availability"
              className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              My availability
            </Link>
            <Link
              href="/artist/bookings"
              className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Booking inbox
            </Link>
          </>
        ) : null}
        {user.role === "moderator" || user.role === "admin" || user.role === "super_admin" ? (
          <Link
            href="/admin/artists"
            className="rounded-md border border-border px-4 py-2 text-center text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Artist verification queue
          </Link>
        ) : null}
      </div>
      <div className="mt-6">
        <AccountActions />
      </div>
    </div>
  );
}

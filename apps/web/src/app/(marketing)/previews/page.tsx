import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { PreviewsListView } from "./previews-list-view";

export default async function PreviewsPage() {
  const hasSession = (await cookies()).has(ACCESS_TOKEN_COOKIE);
  if (!hasSession) redirect("/login");

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl font-semibold text-text-primary">My previews</h1>
        <Link
          href="/previews/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary"
        >
          New preview
        </Link>
      </div>
      <div className="mt-6">
        <PreviewsListView />
      </div>
    </div>
  );
}

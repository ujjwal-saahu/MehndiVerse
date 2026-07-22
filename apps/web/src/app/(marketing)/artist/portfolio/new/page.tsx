import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { CategoryData } from "@/lib/gallery-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { CreateDesignForm } from "./create-design-form";

export default async function NewDesignPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const [meResponse, categoriesResponse] = await Promise.all([
    backendFetch("/auth/me", { headers: authHeaders }),
    backendFetch("/categories", { headers: authHeaders }),
  ]);
  if (!meResponse.ok) {
    redirect("/login");
  }
  const me = (await meResponse.json()) as { role: string };
  const categories = categoriesResponse.ok
    ? ((await categoriesResponse.json()) as CategoryData[])
    : [];

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">New design</h1>
      <div className="mt-6">
        <CreateDesignForm
          categories={categories}
          canSetPremium={
            me.role === "verified_artist" || me.role === "admin" || me.role === "super_admin"
          }
        />
      </div>
    </div>
  );
}

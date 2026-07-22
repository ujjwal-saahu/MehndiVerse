import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { CategoryData, DesignDetailData } from "@/lib/gallery-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { EditDesignForm } from "./edit-design-form";

export default async function EditDesignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const [designResponse, meResponse, categoriesResponse] = await Promise.all([
    backendFetch(`/designs/${id}`, { headers: authHeaders }),
    backendFetch("/auth/me", { headers: authHeaders }),
    backendFetch("/categories", { headers: authHeaders }),
  ]);
  if (designResponse.status === 404) {
    notFound();
  }
  if (!designResponse.ok || !meResponse.ok) {
    redirect("/artist/portfolio");
  }

  const design = (await designResponse.json()) as DesignDetailData;
  const me = (await meResponse.json()) as { role: string };
  const categories = categoriesResponse.ok
    ? ((await categoriesResponse.json()) as CategoryData[])
    : [];

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Edit design</h1>
      <div className="mt-6">
        <EditDesignForm
          initialDesign={design}
          categories={categories}
          canSetPremium={
            me.role === "verified_artist" || me.role === "admin" || me.role === "super_admin"
          }
        />
      </div>
    </div>
  );
}

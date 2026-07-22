import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ArtistDocumentData, ArtistProfileData, AuditLogListData } from "@/lib/artist-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { ArtistReviewView } from "./artist-review-view";

const STAFF_ROLES = new Set(["moderator", "admin", "super_admin"]);

export default async function AdminArtistDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const meResponse = await backendFetch("/auth/me", { headers: authHeaders });
  if (!meResponse.ok) {
    redirect("/login");
  }
  const me = (await meResponse.json()) as { id: string; role: string };
  if (!STAFF_ROLES.has(me.role)) {
    redirect("/account");
  }

  const [profileResponse, documentsResponse, auditLogResponse] = await Promise.all([
    backendFetch(`/admin/artists/${id}`, { headers: authHeaders }),
    backendFetch(`/admin/artists/${id}/documents`, { headers: authHeaders }),
    backendFetch(`/admin/artists/${id}/audit-log?limit=20`, { headers: authHeaders }),
  ]);

  if (profileResponse.status === 404) {
    notFound();
  }
  if (!profileResponse.ok) {
    redirect("/admin/artists");
  }

  const profile = (await profileResponse.json()) as ArtistProfileData;
  const documents = documentsResponse.ok
    ? ((await documentsResponse.json()) as ArtistDocumentData[])
    : [];
  const auditLog = auditLogResponse.ok
    ? ((await auditLogResponse.json()) as AuditLogListData)
    : { items: [], page_info: { next_cursor: null, has_more: false } };

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        {profile.professional_name ?? profile.business_name ?? "Artist application"}
      </h1>
      <div className="mt-6">
        <ArtistReviewView
          artistId={id}
          initialProfile={profile}
          initialDocuments={documents}
          initialAuditLog={auditLog}
          canAct={(me.role === "admin" || me.role === "super_admin") && profile.user_id !== me.id}
          isSelf={profile.user_id === me.id}
        />
      </div>
    </div>
  );
}

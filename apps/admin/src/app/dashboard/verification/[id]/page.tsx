import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import type { ArtistDocumentData, ArtistProfileData } from "@/lib/admin-types";
import { backendFetch } from "@/lib/backend";
import { canEdit, requireStaffUser } from "@/lib/current-staff-user";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { VerificationDetailView } from "./verification-detail-view";

export default async function VerificationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await requireStaffUser();
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const [profileResponse, documentsResponse] = await Promise.all([
    backendFetch(`/admin/artists/${id}`, { headers: authHeaders }),
    backendFetch(`/admin/artists/${id}/documents`, { headers: authHeaders }),
  ]);

  if (profileResponse.status === 404) {
    notFound();
  }
  if (!profileResponse.ok) {
    redirect("/dashboard/verification");
  }

  const profile: ArtistProfileData = await profileResponse.json();
  const documents: ArtistDocumentData[] = documentsResponse.ok
    ? await documentsResponse.json()
    : [];

  return (
    <DashboardShell email={user.email} role={user.role}>
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        {profile.professional_name ?? profile.business_name ?? "Artist application"}
      </h1>
      <div className="mt-6">
        <VerificationDetailView
          initialProfile={profile}
          initialDocuments={documents}
          canAct={canEdit(user.role) && profile.user_id !== user.id}
        />
      </div>
    </DashboardShell>
  );
}

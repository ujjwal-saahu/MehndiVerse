import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ArtistDocumentData, ArtistProfileData } from "@/lib/artist-types";
import { VERIFICATION_STATUS_LABELS } from "@/lib/artist-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

const STATUS_BADGE_CLASSES: Record<string, string> = {
  draft: "bg-surface-variant text-text-secondary",
  submitted: "bg-info-surface text-info",
  under_review: "bg-info-surface text-info",
  more_information_required: "bg-warning-surface text-warning",
  approved: "bg-success-surface text-success",
  rejected: "bg-danger-surface text-danger",
  suspended: "bg-danger-surface text-danger",
};

export default async function ArtistVerificationStatusPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const profileResponse = await backendFetch("/artist/profile", { headers: authHeaders });
  if (profileResponse.status === 403) {
    redirect("/account");
  }
  if (!profileResponse.ok) {
    redirect("/login");
  }
  const profile = (await profileResponse.json()) as ArtistProfileData;

  const documentsResponse = await backendFetch("/artist/documents", { headers: authHeaders });
  const documents = documentsResponse.ok
    ? ((await documentsResponse.json()) as ArtistDocumentData[])
    : [];

  const badgeClass =
    STATUS_BADGE_CLASSES[profile.verification_status] ?? "bg-surface-variant text-text-secondary";

  return (
    <div className="mx-auto max-w-xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Verification status</h1>

      <div className="mt-6 rounded-xl border border-border bg-surface p-6">
        <span className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${badgeClass}`}>
          {VERIFICATION_STATUS_LABELS[profile.verification_status]}
        </span>

        {profile.professional_name ? (
          <p className="mt-4 text-lg font-medium text-text-primary">{profile.professional_name}</p>
        ) : null}

        {(profile.verification_status === "rejected" ||
          profile.verification_status === "suspended") &&
        profile.rejection_reason ? (
          <p className="mt-4 rounded-md border border-danger bg-danger-surface p-4 text-sm text-text-primary">
            <strong>Reason:</strong> {profile.rejection_reason}
          </p>
        ) : null}

        {profile.verification_status === "more_information_required" &&
        profile.more_info_request ? (
          <p className="mt-4 rounded-md border border-warning bg-warning-surface p-4 text-sm text-text-primary">
            <strong>We need more information:</strong> {profile.more_info_request}
          </p>
        ) : null}

        {profile.is_editable ? (
          <Link
            href="/artist/onboarding"
            className="mt-6 inline-block rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
          >
            {profile.verification_status === "draft"
              ? "Continue your application"
              : "Update and resubmit"}
          </Link>
        ) : null}
      </div>

      <div className="mt-6 rounded-xl border border-border bg-surface p-6">
        <h2 className="font-display text-lg font-semibold text-text-primary">Documents</h2>
        {documents.length === 0 ? (
          <p className="mt-2 text-sm text-text-secondary">No documents uploaded yet.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {documents.map((document) => (
              <li key={document.id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="text-text-primary">
                    {document.original_filename ?? document.document_type}
                  </p>
                  <p className="text-text-secondary">{document.document_type.replace(/_/g, " ")}</p>
                </div>
                <span className="text-text-secondary">{document.status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

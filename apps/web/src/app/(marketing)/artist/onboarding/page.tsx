import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ArtistDocumentData, ArtistProfileData } from "@/lib/artist-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

import { OnboardingWizard } from "./onboarding-wizard";

export default async function ArtistOnboardingPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  // GET /artist/profile lazily creates a draft application and promotes the
  // caller's role to `artist` on first visit — this page IS the "become an
  // artist" call to action, so that side effect is intentional here (see
  // docs/artist-verification.md#lazy-onboarding).
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

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        Become a verified artist
      </h1>
      <p className="mt-2 text-text-secondary">
        Tell us about your work. Our team reviews every application before it goes live.
      </p>
      <div className="mt-8">
        <OnboardingWizard initialProfile={profile} initialDocuments={documents} />
      </div>
    </div>
  );
}

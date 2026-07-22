"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SubmitButton } from "@/components/forms/submit-button";
import type {
  ArtistDocumentData,
  ArtistProfileData,
  DocumentType,
  SocialPlatform,
} from "@/lib/artist-types";
import { MISSING_REQUIREMENT_LABELS, SOCIAL_PLATFORMS } from "@/lib/artist-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

const STEPS = [
  "About you",
  "Location & services",
  "Contact & social",
  "Photos",
  "Documents",
  "Review",
] as const;

function TextField({
  label,
  value,
  onChange,
  type = "text",
  ...rest
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type">) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-medium text-text-primary">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-md border border-border bg-background px-3 py-2 text-text-primary focus:border-focus-ring focus:outline-none focus:ring-2 focus:ring-focus-ring"
        {...rest}
      />
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-medium text-text-primary">{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={5}
        className="rounded-md border border-border bg-background px-3 py-2 text-text-primary focus:border-focus-ring focus:outline-none focus:ring-2 focus:ring-focus-ring"
      />
    </label>
  );
}

export function OnboardingWizard({
  initialProfile,
  initialDocuments,
}: {
  initialProfile: ArtistProfileData;
  initialDocuments: ArtistDocumentData[];
}) {
  const router = useRouter();
  const [profile, setProfile] = useState(initialProfile);
  const [documents, setDocuments] = useState(initialDocuments);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState<
    DocumentType | "profile_image" | "cover_image" | null
  >(null);

  const [professionalName, setProfessionalName] = useState(profile.professional_name ?? "");
  const [businessName, setBusinessName] = useState(profile.business_name ?? "");
  const [headline, setHeadline] = useState(profile.headline ?? "");
  const [bio, setBio] = useState(profile.bio ?? "");
  const [yearsExperience, setYearsExperience] = useState(
    profile.years_experience?.toString() ?? "",
  );
  const [country, setCountry] = useState(profile.country ?? "");
  const [city, setCity] = useState(profile.city ?? "");
  const [serviceAreas, setServiceAreas] = useState(profile.service_areas.join(", "));
  const [languages, setLanguages] = useState(profile.languages.join(", "));
  const [contactEmail, setContactEmail] = useState(profile.contact_email ?? "");
  const [contactPhone, setContactPhone] = useState(profile.contact_phone ?? "");
  const [socialLinks, setSocialLinks] = useState<Partial<Record<SocialPlatform, string>>>(
    profile.social_links,
  );

  if (!profile.is_editable) {
    return (
      <div className="rounded-xl border border-border bg-surface p-6">
        <p className="text-text-primary">
          Your application can&apos;t be edited right now — it&apos;s currently{" "}
          <strong>{profile.verification_status.replace(/_/g, " ")}</strong>.
        </p>
        <button
          type="button"
          onClick={() => router.push("/artist/verification-status")}
          className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
        >
          View verification status
        </button>
      </div>
    );
  }

  const savePatch = async (patch: Record<string, unknown>) => {
    setIsSaving(true);
    setError(null);
    try {
      const updated = await mutateJson<ArtistProfileData>("/api/artist/profile", "PATCH", patch);
      setProfile(updated);
      return true;
    } catch (err) {
      setError((err as Error).message);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const goNext = async (patch: Record<string, unknown>) => {
    const ok = await savePatch(patch);
    if (ok) setStep((current) => Math.min(current + 1, STEPS.length - 1));
  };

  const goBack = () => setStep((current) => Math.max(current - 1, 0));

  const refreshAfterUpload = async () => {
    const [freshProfile, freshDocuments] = await Promise.all([
      fetchJson<ArtistProfileData>("/api/artist/profile"),
      fetchJson<ArtistDocumentData[]>("/api/artist/documents"),
    ]);
    setProfile(freshProfile);
    setDocuments(freshDocuments);
  };

  const uploadDocument = async (documentType: DocumentType, file: File) => {
    setIsUploading(documentType);
    setError(null);
    try {
      const formData = new FormData();
      formData.set("file", file);
      formData.set("document_type", documentType);
      const response = await fetch("/api/artist/documents", { method: "POST", body: formData });
      const body = (await response.json()) as { message?: string };
      if (!response.ok) {
        throw new Error(body.message ?? "Could not upload your document.");
      }
      await refreshAfterUpload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsUploading(null);
    }
  };

  const uploadImage = async (field: "profile_image" | "cover_image", file: File) => {
    setIsUploading(field);
    setError(null);
    try {
      const formData = new FormData();
      formData.set("file", file);
      const endpoint =
        field === "profile_image" ? "/api/artist/profile/image" : "/api/artist/profile/cover-image";
      const response = await fetch(endpoint, { method: "POST", body: formData });
      const body = (await response.json()) as { message?: string; image_url?: string };
      if (!response.ok) {
        throw new Error(body.message ?? "Could not upload your image.");
      }
      setProfile((current) => ({
        ...current,
        [field === "profile_image" ? "profile_image_url" : "cover_image_url"]:
          body.image_url ?? null,
      }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsUploading(null);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await mutateJson<ArtistProfileData>("/api/artist/profile/submit", "POST");
      setProfile(updated);
      router.push("/artist/verification-status");
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const idDocument = documents.find(
    (doc) => doc.document_type === "id_proof" && doc.status !== "rejected",
  );
  const businessDocuments = documents.filter((doc) => doc.document_type === "business_license");

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <ol className="mb-6 flex flex-wrap gap-2 text-xs font-medium text-text-secondary">
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={`rounded-full px-3 py-1 ${
              index === step ? "bg-primary text-text-on-primary" : "bg-surface-variant"
            }`}
          >
            {index + 1}. {label}
          </li>
        ))}
      </ol>

      {error ? (
        <p role="alert" className="mb-4 text-sm text-danger">
          {error}
        </p>
      ) : null}

      {step === 0 ? (
        <div className="flex flex-col gap-4">
          <TextField
            label="Professional name"
            value={professionalName}
            onChange={setProfessionalName}
          />
          <TextField
            label="Business name (optional)"
            value={businessName}
            onChange={setBusinessName}
          />
          <TextField
            label="Headline (optional)"
            value={headline}
            onChange={setHeadline}
            maxLength={200}
          />
          <TextAreaField label="Biography" value={bio} onChange={setBio} />
          <TextField
            label="Years of experience"
            type="number"
            min={0}
            max={80}
            value={yearsExperience}
            onChange={setYearsExperience}
          />
          <SubmitButton
            type="button"
            isSubmitting={isSaving}
            onClick={() =>
              goNext({
                professional_name: professionalName || null,
                business_name: businessName || null,
                headline: headline || null,
                bio: bio || null,
                years_experience: yearsExperience ? Number(yearsExperience) : null,
              })
            }
          >
            Continue
          </SubmitButton>
        </div>
      ) : null}

      {step === 1 ? (
        <div className="flex flex-col gap-4">
          <TextField
            label="Country (e.g. IN)"
            value={country}
            onChange={setCountry}
            maxLength={2}
          />
          <TextField label="City" value={city} onChange={setCity} />
          <TextField
            label="Service areas (comma-separated)"
            value={serviceAreas}
            onChange={setServiceAreas}
          />
          <TextField
            label="Languages (comma-separated)"
            value={languages}
            onChange={setLanguages}
          />
          <div className="flex gap-3">
            <button
              type="button"
              onClick={goBack}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Back
            </button>
            <SubmitButton
              type="button"
              isSubmitting={isSaving}
              onClick={() =>
                goNext({
                  country: country || null,
                  city: city || null,
                  service_areas: serviceAreas
                    .split(",")
                    .map((item) => item.trim())
                    .filter(Boolean),
                  languages: languages
                    .split(",")
                    .map((item) => item.trim())
                    .filter(Boolean),
                })
              }
            >
              Continue
            </SubmitButton>
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="flex flex-col gap-4">
          <TextField
            label="Contact email (optional)"
            type="email"
            value={contactEmail}
            onChange={setContactEmail}
          />
          <TextField
            label="Contact phone (optional)"
            value={contactPhone}
            onChange={setContactPhone}
          />
          {SOCIAL_PLATFORMS.map((platform) => (
            <TextField
              key={platform}
              label={`${platform.charAt(0).toUpperCase()}${platform.slice(1)} link (optional)`}
              value={socialLinks[platform] ?? ""}
              onChange={(value) =>
                setSocialLinks((current) => {
                  const next = { ...current };
                  if (value) next[platform] = value;
                  else delete next[platform];
                  return next;
                })
              }
              placeholder="https://…"
            />
          ))}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={goBack}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Back
            </button>
            <SubmitButton
              type="button"
              isSubmitting={isSaving}
              onClick={() =>
                goNext({
                  contact_email: contactEmail || null,
                  contact_phone: contactPhone || null,
                  social_links: socialLinks,
                })
              }
            >
              Continue
            </SubmitButton>
          </div>
        </div>
      ) : null}

      {step === 3 ? (
        <div className="flex flex-col gap-6">
          <div>
            <p className="text-sm font-medium text-text-primary">Profile photo (optional)</p>
            {profile.profile_image_url ? (
              <div className="relative mt-2 h-24 w-24 overflow-hidden rounded-full bg-surface-variant">
                <Image
                  src={profile.profile_image_url}
                  alt=""
                  fill
                  sizes="96px"
                  className="object-cover"
                />
              </div>
            ) : null}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={isUploading === "profile_image"}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadImage("profile_image", file);
              }}
              className="mt-2 text-sm text-text-secondary"
            />
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">Cover photo (optional)</p>
            {profile.cover_image_url ? (
              <div className="relative mt-2 h-24 w-full overflow-hidden rounded-md bg-surface-variant">
                <Image
                  src={profile.cover_image_url}
                  alt=""
                  fill
                  sizes="100vw"
                  className="object-cover"
                />
              </div>
            ) : null}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={isUploading === "cover_image"}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadImage("cover_image", file);
              }}
              className="mt-2 text-sm text-text-secondary"
            />
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={goBack}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => setStep(4)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
            >
              Continue
            </button>
          </div>
        </div>
      ) : null}

      {step === 4 ? (
        <div className="flex flex-col gap-6">
          <div>
            <p className="text-sm font-medium text-text-primary">Identity document (required)</p>
            <p className="text-xs text-text-secondary">
              A government-issued ID or passport, as a JPEG, PNG, or PDF.
            </p>
            {idDocument ? (
              <p className="mt-2 text-sm text-text-secondary">
                Uploaded: {idDocument.original_filename ?? "document"} — status: {idDocument.status}
              </p>
            ) : null}
            <input
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              disabled={isUploading === "id_proof"}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadDocument("id_proof", file);
              }}
              className="mt-2 text-sm text-text-secondary"
            />
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">Business license (optional)</p>
            {businessDocuments.map((doc) => (
              <p key={doc.id} className="mt-1 text-sm text-text-secondary">
                Uploaded: {doc.original_filename ?? "document"} — status: {doc.status}
              </p>
            ))}
            <input
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              disabled={isUploading === "business_license"}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadDocument("business_license", file);
              }}
              className="mt-2 text-sm text-text-secondary"
            />
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={goBack}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => setStep(5)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
            >
              Continue
            </button>
          </div>
        </div>
      ) : null}

      {step === 5 ? (
        <div className="flex flex-col gap-4">
          {profile.missing_requirements.length > 0 ? (
            <div className="rounded-md border border-warning bg-warning-surface p-4">
              <p className="text-sm font-medium text-text-primary">Before you can submit:</p>
              <ul className="mt-2 list-inside list-disc text-sm text-text-secondary">
                {profile.missing_requirements.map((requirement) => (
                  <li key={requirement}>
                    {MISSING_REQUIREMENT_LABELS[requirement] ?? requirement}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-text-secondary">
              Your application is complete. Submit it for review below.
            </p>
          )}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={goBack}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
            >
              Back
            </button>
            <SubmitButton
              type="button"
              isSubmitting={isSubmitting}
              disabled={profile.missing_requirements.length > 0}
              onClick={handleSubmit}
              loadingLabel="Submitting…"
            >
              Submit for review
            </SubmitButton>
          </div>
        </div>
      ) : null}
    </div>
  );
}

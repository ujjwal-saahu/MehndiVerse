"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type {
  ArtistDocumentData,
  ArtistProfileData,
  AuditLogListData,
  DocumentStatus,
} from "@/lib/artist-types";
import { VERIFICATION_STATUS_LABELS } from "@/lib/artist-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

type ReasonActionKind = "reject" | "suspend" | "request-more-information";

const ACTION_LABELS: Record<ReasonActionKind, string> = {
  reject: "Reject application",
  suspend: "Suspend artist",
  "request-more-information": "Request more information",
};

const ACTION_PROMPTS: Record<ReasonActionKind, string> = {
  reject: "Reason for rejection",
  suspend: "Reason for suspension",
  "request-more-information": "What additional information is needed?",
};

function ProfileField({ label, value }: { label: string; value: string | number | null }) {
  if (value === null || value === "") return null;
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">{label}</p>
      <p className="text-text-primary">{value}</p>
    </div>
  );
}

export function ArtistReviewView({
  artistId,
  initialProfile,
  initialDocuments,
  initialAuditLog,
  canAct,
  isSelf,
}: {
  artistId: string;
  initialProfile: ArtistProfileData;
  initialDocuments: ArtistDocumentData[];
  initialAuditLog: AuditLogListData;
  canAct: boolean;
  isSelf: boolean;
}) {
  const router = useRouter();
  const [profile, setProfile] = useState(initialProfile);
  const [documents, setDocuments] = useState(initialDocuments);
  const [auditLog, setAuditLog] = useState(initialAuditLog);
  const [error, setError] = useState<string | null>(null);
  const [isActing, setIsActing] = useState(false);
  const [reasonPanel, setReasonPanel] = useState<ReasonActionKind | null>(null);
  const [reasonText, setReasonText] = useState("");
  const [documentReasonId, setDocumentReasonId] = useState<string | null>(null);
  const [documentReasonText, setDocumentReasonText] = useState("");

  const refreshAuditLog = async () => {
    const fresh = await fetchJson<AuditLogListData>(
      `/api/admin/artists/${artistId}/audit-log?limit=20`,
    );
    setAuditLog(fresh);
  };

  const runAction = async (action: string, body?: Record<string, string>) => {
    setIsActing(true);
    setError(null);
    try {
      const updated = await mutateJson<ArtistProfileData>(
        `/api/admin/artists/${artistId}/${action}`,
        "POST",
        body,
      );
      setProfile(updated);
      setReasonPanel(null);
      setReasonText("");
      await refreshAuditLog();
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsActing(false);
    }
  };

  const confirmReasonAction = () => {
    if (!reasonPanel || !reasonText.trim()) return;
    const key = reasonPanel === "request-more-information" ? "message" : "reason";
    void runAction(reasonPanel, { [key]: reasonText.trim() });
  };

  const reviewDocument = async (
    documentId: string,
    status: DocumentStatus,
    rejectionReason?: string,
  ) => {
    setIsActing(true);
    setError(null);
    try {
      const updated = await mutateJson<ArtistDocumentData>(
        `/api/admin/artists/${artistId}/documents/${documentId}`,
        "PATCH",
        { status, rejection_reason: rejectionReason },
      );
      setDocuments((current) => current.map((doc) => (doc.id === documentId ? updated : doc)));
      setDocumentReasonId(null);
      setDocumentReasonText("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsActing(false);
    }
  };

  const status = profile.verification_status;

  return (
    <div className="flex flex-col gap-6">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <div className="rounded-xl border border-border bg-surface p-6">
        <span className="inline-block rounded-full bg-surface-variant px-3 py-1 text-sm font-medium text-text-secondary">
          {VERIFICATION_STATUS_LABELS[status]}
        </span>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ProfileField label="Professional name" value={profile.professional_name} />
          <ProfileField label="Business name" value={profile.business_name} />
          <ProfileField label="Years of experience" value={profile.years_experience} />
          <ProfileField
            label="Location"
            value={[profile.city, profile.country].filter(Boolean).join(", ")}
          />
          <ProfileField label="Contact email" value={profile.contact_email} />
          <ProfileField label="Contact phone" value={profile.contact_phone} />
          <ProfileField label="Service areas" value={profile.service_areas.join(", ")} />
          <ProfileField label="Languages" value={profile.languages.join(", ")} />
        </div>
        {profile.bio ? (
          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">
              Biography
            </p>
            <p className="text-text-primary">{profile.bio}</p>
          </div>
        ) : null}

        {isSelf ? (
          <p className="mt-6 rounded-md border border-warning bg-warning-surface p-4 text-sm text-text-primary">
            This is your own application — you cannot review it. Ask another administrator.
          </p>
        ) : canAct ? (
          <div className="mt-6 flex flex-wrap gap-3">
            {status === "submitted" ? (
              <button
                type="button"
                disabled={isActing}
                onClick={() => void runAction("start-review")}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:opacity-60"
              >
                Start review
              </button>
            ) : null}
            {status === "under_review" ? (
              <>
                <button
                  type="button"
                  disabled={isActing}
                  onClick={() => void runAction("approve")}
                  className="rounded-md border border-success bg-success-surface px-4 py-2 text-sm font-medium text-success hover:opacity-90 disabled:opacity-60"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={isActing}
                  onClick={() => setReasonPanel("reject")}
                  className="rounded-md border border-danger bg-danger-surface px-4 py-2 text-sm font-medium text-danger hover:opacity-90 disabled:opacity-60"
                >
                  Reject
                </button>
                <button
                  type="button"
                  disabled={isActing}
                  onClick={() => setReasonPanel("request-more-information")}
                  className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-60"
                >
                  Request more information
                </button>
              </>
            ) : null}
            {status === "approved" ? (
              <button
                type="button"
                disabled={isActing}
                onClick={() => setReasonPanel("suspend")}
                className="rounded-md border border-danger bg-danger-surface px-4 py-2 text-sm font-medium text-danger hover:opacity-90 disabled:opacity-60"
              >
                Suspend
              </button>
            ) : null}
            {status === "suspended" ? (
              <button
                type="button"
                disabled={isActing}
                onClick={() => void runAction("approve")}
                className="rounded-md border border-success bg-success-surface px-4 py-2 text-sm font-medium text-success hover:opacity-90 disabled:opacity-60"
              >
                Reinstate
              </button>
            ) : null}
          </div>
        ) : null}

        {reasonPanel ? (
          <div className="mt-4 rounded-md border border-border bg-background p-4">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-medium text-text-primary">
                {ACTION_PROMPTS[reasonPanel]}
              </span>
              <textarea
                value={reasonText}
                onChange={(event) => setReasonText(event.target.value)}
                rows={3}
                className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
              />
            </label>
            <div className="mt-3 flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setReasonPanel(null);
                  setReasonText("");
                }}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isActing || !reasonText.trim()}
                onClick={confirmReasonAction}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:opacity-60"
              >
                {ACTION_LABELS[reasonPanel]}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="font-display text-lg font-semibold text-text-primary">Documents</h2>
        {documents.length === 0 ? (
          <p className="mt-2 text-sm text-text-secondary">No documents uploaded.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-4">
            {documents.map((document) => (
              <li key={document.id} className="rounded-md border border-border p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-text-primary">
                      {document.original_filename ?? document.document_type}
                    </p>
                    <p className="text-sm text-text-secondary">
                      {document.document_type.replace(/_/g, " ")} · {document.status}
                    </p>
                  </div>
                  <a
                    href={document.view_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    View
                  </a>
                </div>
                {document.rejection_reason ? (
                  <p className="mt-2 text-sm text-danger">Rejected: {document.rejection_reason}</p>
                ) : null}
                {canAct && document.status === "pending" ? (
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      disabled={isActing}
                      onClick={() => void reviewDocument(document.id, "approved")}
                      className="rounded-md border border-success bg-success-surface px-3 py-1.5 text-sm font-medium text-success hover:opacity-90 disabled:opacity-60"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={isActing}
                      onClick={() => setDocumentReasonId(document.id)}
                      className="rounded-md border border-danger bg-danger-surface px-3 py-1.5 text-sm font-medium text-danger hover:opacity-90 disabled:opacity-60"
                    >
                      Reject
                    </button>
                  </div>
                ) : null}
                {documentReasonId === document.id ? (
                  <div className="mt-3 flex flex-col gap-2">
                    <textarea
                      value={documentReasonText}
                      onChange={(event) => setDocumentReasonText(event.target.value)}
                      rows={2}
                      placeholder="Reason for rejecting this document"
                      className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setDocumentReasonId(null);
                          setDocumentReasonText("");
                        }}
                        className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={isActing || !documentReasonText.trim()}
                        onClick={() =>
                          void reviewDocument(document.id, "rejected", documentReasonText.trim())
                        }
                        className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:opacity-60"
                      >
                        Confirm rejection
                      </button>
                    </div>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="font-display text-lg font-semibold text-text-primary">Audit log</h2>
        {auditLog.items.length === 0 ? (
          <p className="mt-2 text-sm text-text-secondary">No actions recorded yet.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {auditLog.items.map((entry) => (
              <li key={entry.id} className="text-sm">
                <p className="text-text-primary">
                  <span className="font-medium">{entry.actor_display_name ?? "System"}</span>{" "}
                  {entry.action.replace("artist_verification.", "").replace(/_/g, " ")}
                </p>
                <p className="text-text-secondary">{new Date(entry.created_at).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

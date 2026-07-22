"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { ReasonDialog } from "@/components/forms/reason-dialog";
import { mutateJson } from "@/lib/admin-client";
import type { ArtistDocumentData, ArtistProfileData } from "@/lib/admin-types";

type ReasonAction = "reject" | "request-more-information" | "suspend";

const REASON_ACTION_LABELS: Record<ReasonAction, { title: string; confirmLabel: string }> = {
  reject: { title: "Reject application", confirmLabel: "Reject" },
  "request-more-information": {
    title: "Request more information",
    confirmLabel: "Send request",
  },
  suspend: { title: "Suspend artist", confirmLabel: "Suspend" },
};

export function VerificationDetailView({
  initialProfile,
  initialDocuments,
  canAct,
}: {
  initialProfile: ArtistProfileData;
  initialDocuments: ArtistDocumentData[];
  canAct: boolean;
}) {
  const router = useRouter();
  const [profile, setProfile] = useState(initialProfile);
  const [documents] = useState(initialDocuments);
  const [reasonAction, setReasonAction] = useState<ReasonAction | null>(null);
  const [confirmReactivate, setConfirmReactivate] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAction = (path: string, body?: unknown) => {
    setIsSubmitting(true);
    setError(null);
    return mutateJson<ArtistProfileData>(`/api/admin/artists/${profile.id}/${path}`, "POST", body)
      .then((updated) => {
        setProfile(updated);
        setReasonAction(null);
        setConfirmReactivate(false);
        router.refresh();
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsSubmitting(false));
  };

  const submitReasonAction = (reason: string) => {
    if (reasonAction === "reject") {
      void runAction("reject", { reason });
    } else if (reasonAction === "request-more-information") {
      void runAction("request-more-information", { message: reason });
    } else if (reasonAction === "suspend") {
      void runAction("suspend", { reason });
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-border bg-surface p-4">
        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-text-secondary">Status</dt>
            <dd className="font-medium text-text-primary">{profile.verification_status}</dd>
          </div>
          <div>
            <dt className="text-text-secondary">City / Country</dt>
            <dd className="text-text-primary">
              {[profile.city, profile.country].filter(Boolean).join(", ") || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-text-secondary">Contact</dt>
            <dd className="text-text-primary">
              {profile.contact_email ?? "—"}{" "}
              {profile.contact_phone ? `· ${profile.contact_phone}` : ""}
            </dd>
          </div>
          <div>
            <dt className="text-text-secondary">Submitted</dt>
            <dd className="text-text-primary">
              {profile.submitted_at ? new Date(profile.submitted_at).toLocaleString() : "—"}
            </dd>
          </div>
        </dl>
        {profile.bio ? <p className="mt-4 text-sm text-text-primary">{profile.bio}</p> : null}
        {profile.rejection_reason ? (
          <p className="mt-4 text-sm text-danger">Rejection reason: {profile.rejection_reason}</p>
        ) : null}
        {profile.more_info_request ? (
          <p className="mt-4 text-sm text-warning">
            More information requested: {profile.more_info_request}
          </p>
        ) : null}
      </section>

      <section>
        <h2 className="font-display text-lg font-semibold text-text-primary">Documents</h2>
        {documents.length === 0 ? (
          <p className="mt-2 text-sm text-text-secondary">No documents uploaded yet.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between rounded-md border border-border bg-surface p-3 text-sm"
              >
                <div>
                  <p className="text-text-primary">
                    {doc.document_type} · {doc.status}
                  </p>
                  {doc.original_filename ? (
                    <p className="text-text-secondary">{doc.original_filename}</p>
                  ) : null}
                </div>
                <a
                  href={doc.view_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm font-medium text-primary hover:underline"
                >
                  View
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>

      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      {canAct ? (
        <section className="flex flex-wrap gap-3">
          {profile.verification_status === "submitted" ? (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => void runAction("start-review")}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
            >
              Start review
            </button>
          ) : null}
          {profile.verification_status === "under_review" ||
          profile.verification_status === "submitted" ? (
            <>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => void runAction("approve")}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
              >
                Approve
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setReasonAction("reject")}
                className="rounded-md border border-danger px-4 py-2 text-sm font-medium text-danger hover:bg-danger-surface disabled:opacity-50"
              >
                Reject
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setReasonAction("request-more-information")}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
              >
                Request more information
              </button>
            </>
          ) : null}
          {profile.verification_status === "approved" ? (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => setReasonAction("suspend")}
              className="rounded-md border border-danger px-4 py-2 text-sm font-medium text-danger hover:bg-danger-surface disabled:opacity-50"
            >
              Suspend
            </button>
          ) : null}
          {profile.verification_status === "suspended" ? (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => setConfirmReactivate(true)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
            >
              Reactivate
            </button>
          ) : null}
        </section>
      ) : null}

      <ReasonDialog
        isOpen={reasonAction !== null}
        title={reasonAction ? REASON_ACTION_LABELS[reasonAction].title : ""}
        confirmLabel={reasonAction ? REASON_ACTION_LABELS[reasonAction].confirmLabel : "Submit"}
        isSubmitting={isSubmitting}
        error={error}
        onConfirm={submitReasonAction}
        onCancel={() => setReasonAction(null)}
      />

      <ConfirmDialog
        isOpen={confirmReactivate}
        title="Reactivate artist"
        message="This artist will be able to accept bookings again."
        confirmLabel="Reactivate"
        isSubmitting={isSubmitting}
        onConfirm={() => void runAction("reactivate")}
        onCancel={() => setConfirmReactivate(false)}
      />
    </div>
  );
}

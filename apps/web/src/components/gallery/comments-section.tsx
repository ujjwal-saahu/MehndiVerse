"use client";

import { useCallback, useEffect, useState } from "react";

import { ReportButton } from "@/components/feedback/report-button";
import type { CommentData, CommentListData, ReplyData } from "@/lib/community-types";
import { fetchJson, mutateJson, sendRequest } from "@/lib/gallery-client";
import { useCurrentUser } from "@/lib/use-current-user";

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: CommentData[] };

function timeAgo(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

function CommentComposer({
  onSubmit,
  placeholder = "Add a comment…",
  submitLabel = "Post",
  autoFocus = false,
}: {
  onSubmit: (body: string) => Promise<void>;
  placeholder?: string;
  submitLabel?: string;
  autoFocus?: boolean;
}) {
  const [body, setBody] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    if (!body.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    onSubmit(body.trim())
      .then(() => setBody(""))
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsSubmitting(false));
  };

  return (
    <div className="flex flex-col gap-2">
      <textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        rows={2}
        maxLength={2000}
        className="w-full rounded-md border border-border bg-background p-2 text-sm text-text-primary"
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={submit}
          disabled={isSubmitting || !body.trim()}
          className="self-start rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-text-on-primary disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Posting…" : submitLabel}
        </button>
        {error ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function CommentRow({
  comment,
  currentUserId,
  onEdit,
  onDelete,
}: {
  comment: CommentData | ReplyData;
  currentUserId: string | null;
  onEdit: (id: string, body: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editBody, setEditBody] = useState(comment.body);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isOwner = currentUserId !== null && currentUserId === comment.user_id;

  if (isEditing) {
    return (
      <div className="flex flex-col gap-2">
        <textarea
          value={editBody}
          onChange={(event) => setEditBody(event.target.value)}
          rows={2}
          maxLength={2000}
          className="w-full rounded-md border border-border bg-background p-2 text-sm text-text-primary"
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={isBusy || !editBody.trim()}
            onClick={() => {
              setIsBusy(true);
              onEdit(comment.id, editBody.trim())
                .then(() => setIsEditing(false))
                .catch((err: Error) => setError(err.message))
                .finally(() => setIsBusy(false));
            }}
            className="rounded-md border border-border px-3 py-1 text-xs font-medium text-text-primary hover:bg-surface-variant disabled:opacity-60"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              setEditBody(comment.body);
              setIsEditing(false);
            }}
            className="text-xs text-text-secondary hover:underline"
          >
            Cancel
          </button>
          {error ? (
            <p role="alert" className="text-xs text-danger">
              {error}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-text-primary">{comment.body}</p>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-secondary">
        <span>{comment.user_display_name ?? "Someone"}</span>
        <span>· {timeAgo(comment.created_at)}</span>
        {isOwner ? (
          <>
            <button type="button" onClick={() => setIsEditing(true)} className="hover:underline">
              Edit
            </button>
            <button
              type="button"
              onClick={() => void onDelete(comment.id)}
              className="hover:underline"
            >
              Delete
            </button>
          </>
        ) : (
          <ReportButton endpoint={`/api/comments/${comment.id}/report`} label="Report" />
        )}
      </div>
    </div>
  );
}

export function CommentsSection({ designId }: { designId: string }) {
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const currentUser = useCurrentUser();

  const load = useCallback(() => {
    fetchJson<CommentListData>(`/api/designs/${designId}/comments`)
      .then((data) => setState({ status: "ready", items: data.items }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  }, [designId]);

  useEffect(() => {
    load();
  }, [load]);

  const createComment = (body: string, parentCommentId: string | null) =>
    mutateJson(`/api/designs/${designId}/comments`, "POST", {
      body,
      parent_comment_id: parentCommentId,
    }).then(() => {
      setReplyingTo(null);
      load();
    });

  const editComment = (id: string, body: string) =>
    mutateJson(`/api/comments/${id}`, "PATCH", { body }).then(() => load());

  const deleteComment = (id: string) =>
    sendRequest(`/api/comments/${id}`, "DELETE").then(() => load());

  return (
    <section className="mt-12">
      <h2 className="font-display text-xl font-semibold text-text-primary">Comments</h2>

      <div className="mt-4">
        <CommentComposer onSubmit={(body) => createComment(body, null)} />
      </div>

      <div className="mt-6 flex flex-col gap-6">
        {state.status === "loading" ? (
          <p className="text-sm text-text-secondary">Loading comments…</p>
        ) : state.status === "error" ? (
          <p role="alert" className="text-sm text-danger">
            {state.message}
          </p>
        ) : state.items.length === 0 ? (
          <p className="text-sm text-text-secondary">
            No comments yet. Be the first to say something.
          </p>
        ) : (
          state.items.map((comment) => (
            <div key={comment.id} className="rounded-lg border border-border bg-surface p-3">
              <CommentRow
                comment={comment}
                currentUserId={currentUser?.id ?? null}
                onEdit={editComment}
                onDelete={deleteComment}
              />

              {comment.replies.length > 0 ? (
                <div className="mt-3 flex flex-col gap-3 border-l border-border pl-4">
                  {comment.replies.map((reply) => (
                    <CommentRow
                      key={reply.id}
                      comment={reply}
                      currentUserId={currentUser?.id ?? null}
                      onEdit={editComment}
                      onDelete={deleteComment}
                    />
                  ))}
                </div>
              ) : null}

              <div className="mt-2">
                {replyingTo === comment.id ? (
                  <CommentComposer
                    onSubmit={(body) => createComment(body, comment.id)}
                    placeholder="Write a reply…"
                    submitLabel="Reply"
                    autoFocus
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => setReplyingTo(comment.id)}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Reply
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

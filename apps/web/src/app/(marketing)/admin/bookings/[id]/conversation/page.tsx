import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { MessagePageData } from "@/lib/messaging-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function AdminBookingConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch(`/admin/bookings/${id}/conversation/messages`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (response.status === 403) {
    redirect("/");
  }
  if (response.status === 404) {
    notFound();
  }
  if (!response.ok) {
    redirect("/");
  }
  const page = (await response.json()) as MessagePageData;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">
        Conversation — dispute review
      </h1>
      <p className="mt-1 text-sm text-text-secondary">
        This view is staff-only and every visit is recorded to the audit log.
      </p>

      <ul className="mt-6 flex flex-col gap-2">
        {page.items.map((message) => (
          <li key={message.id} className="rounded-lg border border-border bg-surface p-3 text-sm">
            {message.body ? <p className="text-text-primary">{message.body}</p> : null}
            {message.attachment_url ? (
              <p className="mt-1 text-xs text-text-secondary">
                <a
                  href={message.attachment_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline"
                >
                  View attachment
                </a>
              </p>
            ) : null}
            <p className="mt-1 text-xs text-text-secondary">
              {new Date(message.created_at).toLocaleString()} · sender {message.sender_id}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

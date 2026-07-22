import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";
import type { ConversationSummaryData } from "@/lib/messaging-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function MessagesPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch("/conversations", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const conversations = response.ok ? ((await response.json()) as ConversationSummaryData[]) : [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Messages</h1>
      <p className="mt-1 text-text-secondary">Conversations about your bookings.</p>

      {conversations.length === 0 ? (
        <p className="mt-8 text-sm text-text-secondary">No conversations yet.</p>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <Link
                href={`/bookings/${conversation.booking.booking_id}`}
                className="flex items-center justify-between rounded-xl border border-border bg-surface p-4 hover:bg-surface-variant"
              >
                <div>
                  <p className="font-medium text-text-primary">
                    {conversation.other_party_display_name ?? "Conversation"}
                    {conversation.booking.service_name
                      ? ` · ${conversation.booking.service_name}`
                      : ""}
                  </p>
                  <p className="mt-1 text-sm text-text-secondary">
                    {conversation.last_message_preview ?? "No messages yet"}
                  </p>
                </div>
                {conversation.unread_count > 0 ? (
                  <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-on-primary">
                    {conversation.unread_count}
                  </span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

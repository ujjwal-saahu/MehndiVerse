"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import type { MessageData } from "@/lib/messaging-types";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T | { message: string }> {
  const response = await fetch(url, init);
  const json = await response.json();
  if (!response.ok) return json as { message: string };
  return json as T;
}

export function BookingConversation({ bookingId }: { bookingId: string }) {
  const [messages, setMessages] = useState<MessageData[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    fetchJson<{ id: string }>(`/api/bookings/${bookingId}/conversation`).then((conversation) => {
      if ("message" in conversation) {
        setUnavailable(true);
        return;
      }
      fetchJson<{
        items: MessageData[];
        page_info: { next_cursor: string | null; has_more: boolean };
      }>(`/api/bookings/${bookingId}/conversation/messages`).then((page) => {
        if ("message" in page) {
          setError(page.message);
          return;
        }
        setMessages([...page.items].reverse());
        setNextCursor(page.page_info.has_more ? page.page_info.next_cursor : null);
        void fetch(`/api/bookings/${bookingId}/conversation/read`, { method: "POST" });
      });
    });
  }, [bookingId]);

  const loadOlder = async () => {
    if (!nextCursor) return;
    setIsBusy(true);
    try {
      const page = await fetchJson<{
        items: MessageData[];
        page_info: { next_cursor: string | null; has_more: boolean };
      }>(
        `/api/bookings/${bookingId}/conversation/messages?cursor=${encodeURIComponent(nextCursor)}`,
      );
      if ("message" in page) {
        setError(page.message);
        return;
      }
      setMessages((current) => [...[...page.items].reverse(), ...(current ?? [])]);
      setNextCursor(page.page_info.has_more ? page.page_info.next_cursor : null);
    } finally {
      setIsBusy(false);
    }
  };

  const send = async () => {
    if (!text.trim()) return;
    setIsBusy(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.set("body", text.trim());
      const response = await fetch(`/api/bookings/${bookingId}/conversation/messages`, {
        method: "POST",
        body: formData,
      });
      const json = await response.json();
      if (!response.ok) {
        setError(json.message);
        return;
      }
      setMessages((current) => [...(current ?? []), json as MessageData]);
      setText("");
    } finally {
      setIsBusy(false);
    }
  };

  const sendImage = async (file: File) => {
    setIsBusy(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.set("file", file);
      const response = await fetch(`/api/bookings/${bookingId}/conversation/messages`, {
        method: "POST",
        body: formData,
      });
      const json = await response.json();
      if (!response.ok) {
        setError(json.message);
        return;
      }
      setMessages((current) => [...(current ?? []), json as MessageData]);
    } finally {
      setIsBusy(false);
    }
  };

  const report = async (messageId: string) => {
    const reason = window.prompt("Why are you reporting this message?");
    if (!reason) return;
    await fetch(`/api/messages/${messageId}/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
  };

  if (unavailable) return null;

  return (
    <section className="mt-8">
      <h2 className="font-medium text-text-primary">Messages</h2>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}

      {nextCursor ? (
        <button
          type="button"
          onClick={() => void loadOlder()}
          disabled={isBusy}
          className="mt-2 text-sm text-primary hover:underline disabled:opacity-50"
        >
          Load older messages
        </button>
      ) : null}

      <div className="mt-3 flex flex-col gap-2">
        {messages === null ? (
          <p className="text-sm text-text-secondary">Loading…</p>
        ) : messages.length === 0 ? (
          <p className="text-sm text-text-secondary">No messages yet. Say hello!</p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className="rounded-lg border border-border bg-surface p-3 text-sm"
            >
              {message.body ? <p className="text-text-primary">{message.body}</p> : null}
              {message.attachment_url ? (
                <div className="relative mt-2 h-40 w-40 overflow-hidden rounded-md">
                  <Image src={message.attachment_url} alt="" fill className="object-cover" />
                </div>
              ) : null}
              <div className="mt-1 flex items-center justify-between text-xs text-text-secondary">
                <span>
                  {new Date(message.created_at).toLocaleString()} ·{" "}
                  {message.is_read ? "Read" : "Sent"}
                </span>
                <button
                  type="button"
                  onClick={() => void report(message.id)}
                  className="hover:underline"
                >
                  Report
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
          placeholder="Write a message…"
          className="flex-1 rounded-md border border-border px-3 py-2 text-sm text-text-primary"
        />
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void sendImage(file);
          }}
          className="text-xs text-text-primary"
        />
        <button
          type="button"
          onClick={() => void send()}
          disabled={isBusy || !text.trim()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-on-primary disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </section>
  );
}

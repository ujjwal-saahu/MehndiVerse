"use client";

import { useEffect, useState } from "react";

import type { NotificationData } from "@/lib/notification-types";

export function NotificationsView() {
  const [notifications, setNotifications] = useState<NotificationData[] | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isBusy, setIsBusy] = useState(false);

  const load = async () => {
    const response = await fetch("/api/notifications");
    if (!response.ok) return;
    const body = await response.json();
    setNotifications(body.items);
    setUnreadCount(body.unread_count);
  };

  useEffect(() => {
    fetch("/api/notifications")
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (!body) return;
        setNotifications(body.items);
        setUnreadCount(body.unread_count);
      });
  }, []);

  const markRead = async (id: string) => {
    setIsBusy(true);
    try {
      await fetch(`/api/notifications/${id}/read`, { method: "POST" });
      await load();
    } finally {
      setIsBusy(false);
    }
  };

  const markAllRead = async () => {
    setIsBusy(true);
    try {
      await fetch("/api/notifications/read-all", { method: "POST" });
      await load();
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">{unreadCount} unread</p>
        <button
          type="button"
          onClick={() => void markAllRead()}
          disabled={isBusy || unreadCount === 0}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          Mark all read
        </button>
      </div>

      {notifications === null ? (
        <p className="mt-6 text-sm text-text-secondary">Loading…</p>
      ) : notifications.length === 0 ? (
        <p className="mt-6 text-sm text-text-secondary">No notifications yet.</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-2">
          {notifications.map((notification) => (
            <li
              key={notification.id}
              className={`rounded-lg border border-border p-4 ${notification.is_read ? "bg-surface" : "bg-surface-variant"}`}
            >
              <div className="flex items-center justify-between">
                <p className="font-medium text-text-primary">{notification.title}</p>
                {!notification.is_read ? (
                  <button
                    type="button"
                    onClick={() => void markRead(notification.id)}
                    disabled={isBusy}
                    className="text-xs text-primary hover:underline disabled:opacity-50"
                  >
                    Mark read
                  </button>
                ) : null}
              </div>
              <p className="mt-1 text-sm text-text-secondary">{notification.body}</p>
              <p className="mt-1 text-xs text-text-secondary">
                {new Date(notification.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

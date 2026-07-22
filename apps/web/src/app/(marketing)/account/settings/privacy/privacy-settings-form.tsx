"use client";

import { useState } from "react";

import type { BlockedUserData, PreferencesData } from "@/lib/profile-types";

type PrivacyField = "profile_visibility" | "show_location" | "allow_messages_from_strangers";

export function PrivacySettingsForm({
  preferences,
  initialBlockedUsers,
}: {
  preferences: PreferencesData;
  initialBlockedUsers: BlockedUserData[];
}) {
  const [prefs, setPrefs] = useState(preferences);
  const [blockedUsers, setBlockedUsers] = useState(initialBlockedUsers);
  const [unblockError, setUnblockError] = useState<string | null>(null);

  const onUpdate = async (field: PrivacyField, value: boolean | string) => {
    setPrefs((current) => ({ ...current, [field]: value }));
    await fetch("/api/preferences", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: value }),
    });
  };

  const onUnblock = async (userId: string) => {
    setUnblockError(null);
    const response = await fetch(`/api/blocks/${userId}`, { method: "DELETE" });
    if (!response.ok) {
      setUnblockError("Could not unblock this user. Please try again.");
      return;
    }
    setBlockedUsers((current) => current.filter((user) => user.user_id !== userId));
  };

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.profile_visibility === "private"}
            onChange={(event) =>
              onUpdate("profile_visibility", event.target.checked ? "private" : "public")
            }
          />
          Private profile
          <span className="text-sm text-text-secondary">
            (only you and staff can view your profile)
          </span>
        </label>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.show_location}
            onChange={(event) => onUpdate("show_location", event.target.checked)}
          />
          Show my location
        </label>
        <label className="flex items-center gap-2 text-text-primary">
          <input
            type="checkbox"
            checked={prefs.allow_messages_from_strangers}
            onChange={(event) => onUpdate("allow_messages_from_strangers", event.target.checked)}
          />
          Allow messages from anyone
          <span className="text-sm text-text-secondary">(otherwise only booking-related)</span>
        </label>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-text-primary">Blocked users</h2>
        {unblockError ? (
          <p role="alert" className="text-sm text-danger">
            {unblockError}
          </p>
        ) : null}
        {blockedUsers.length === 0 ? (
          <p className="text-sm text-text-secondary">You haven&apos;t blocked anyone.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {blockedUsers.map((user) => (
              <li
                key={user.user_id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2"
              >
                <span className="text-text-primary">{user.display_name ?? "Unknown user"}</span>
                <button
                  type="button"
                  onClick={() => onUnblock(user.user_id)}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  Unblock
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

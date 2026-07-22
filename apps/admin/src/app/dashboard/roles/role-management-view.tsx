"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import type { AdminUserData } from "@/lib/admin-types";
import { fetchJson, mutateJson } from "@/lib/admin-client";

const ROLE_OPTIONS = ["customer", "artist", "moderator", "administrator", "super_administrator"];

interface PendingChange {
  user: AdminUserData;
  newRole: string;
}

export function RoleManagementView({ currentUserId }: { currentUserId: string }) {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<AdminUserData[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<Record<string, string>>({});
  const [pendingChange, setPendingChange] = useState<PendingChange | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const runSearch = () => {
    if (!search.trim()) return;
    setIsSearching(true);
    setSearchError(null);
    fetchJson<{ items: AdminUserData[] }>(
      `/api/admin/users?${new URLSearchParams({ search: search.trim(), page_size: "20" })}`,
    )
      .then((data) => setResults(data.items))
      .catch((error: Error) => setSearchError(error.message))
      .finally(() => setIsSearching(false));
  };

  const submitRoleChange = () => {
    if (!pendingChange) return;
    setIsSubmitting(true);
    setActionError(null);
    mutateJson(`/api/admin/users/${pendingChange.user.id}/role`, "PATCH", {
      role: pendingChange.newRole,
    })
      .then(() => {
        setResults((current) =>
          current.map((u) =>
            u.id === pendingChange.user.id ? { ...u, role: pendingChange.newRole } : u,
          ),
        );
        setPendingChange(null);
      })
      .catch((error: Error) => setActionError(error.message))
      .finally(() => setIsSubmitting(false));
  };

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") runSearch();
          }}
          placeholder="Search by email…"
          aria-label="Search users by email"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
        />
        <button
          type="button"
          onClick={runSearch}
          disabled={isSearching || !search.trim()}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:opacity-50"
        >
          Search
        </button>
      </div>

      {searchError ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          {searchError}
        </p>
      ) : null}

      <ul className="mt-4 flex flex-col gap-3">
        {results.map((user) => {
          const isSelf = user.id === currentUserId;
          const nextRole = selectedRole[user.id] ?? user.role;
          return (
            <li
              key={user.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface p-4"
            >
              <div>
                <p className="font-medium text-text-primary">{user.email}</p>
                <p className="text-sm text-text-secondary">Current role: {user.role}</p>
              </div>
              {isSelf ? (
                <p className="text-sm text-text-secondary">You cannot change your own role.</p>
              ) : (
                <div className="flex items-center gap-2">
                  <select
                    value={nextRole}
                    onChange={(event) =>
                      setSelectedRole((current) => ({ ...current, [user.id]: event.target.value }))
                    }
                    aria-label={`New role for ${user.email}`}
                    className="rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary"
                  >
                    {ROLE_OPTIONS.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={nextRole === user.role}
                    onClick={() => setPendingChange({ user, newRole: nextRole })}
                    className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-text-on-primary disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Update role
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <ConfirmDialog
        isOpen={pendingChange !== null}
        title="Change role"
        message={
          pendingChange
            ? `Change ${pendingChange.user.email}'s role from ${pendingChange.user.role} to ${pendingChange.newRole}?`
            : ""
        }
        confirmLabel="Change role"
        isSubmitting={isSubmitting}
        error={actionError}
        onConfirm={submitRoleChange}
        onCancel={() => setPendingChange(null)}
      />
    </div>
  );
}

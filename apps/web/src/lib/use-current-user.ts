"use client";

import { useEffect, useState } from "react";

export interface CurrentUserData {
  id: string;
  email: string;
  role: string;
}

/** Fetches the viewer's own identity for client components that need to
 * compare "is this mine?" (e.g. showing edit/delete on your own comment) —
 * see app/api/routes/auth.py's `/auth/me`. Every other page in this app
 * resolves this server-side from the cookie already, but the comments
 * section renders entirely client-side (like the rest of the design-detail
 * view), so it fetches its own copy via `/api/auth/me`. */
export function useCurrentUser(): CurrentUserData | null {
  const [user, setUser] = useState<CurrentUserData | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth/me")
      .then((response) => (response.ok ? response.json() : null))
      .then((data: CurrentUserData | null) => {
        if (!cancelled) setUser(data);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return user;
}

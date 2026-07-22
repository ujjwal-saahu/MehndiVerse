"use client";

import { useEffect, useState } from "react";

/** Tracks browser online/offline state so views can distinguish "the
 * request failed because you're offline" from a generic server error — see
 * docs/design-gallery.md#offline-friendly-error-state. The lazy initializer
 * reads `navigator.onLine` directly (guarded for SSR, where `navigator`
 * doesn't exist) rather than defaulting to `true` and correcting it via a
 * synchronous `setState` inside an effect on mount. This value is never
 * used in the initial server-rendered markup (only in error messages shown
 * after a failed fetch), so there's no hydration-mismatch risk. */
export function useOnlineStatus(): boolean {
  const [isOnline, setIsOnline] = useState(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return isOnline;
}

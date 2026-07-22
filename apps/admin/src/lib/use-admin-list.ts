"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchJson } from "@/lib/admin-client";
import type { AdminPageInfo } from "@/lib/admin-types";

export interface ListResponse<T> {
  items: T[];
  page_info: AdminPageInfo;
}

type ListState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ListResponse<T> };

/** Fetch-on-url-change for every admin list page — `url` is a fully-built
 * query string (page/search/filters/sort all folded in by the caller), so
 * this hook only owns the request lifecycle, not the many different filter
 * shapes each module needs. See docs/admin-dashboard.md#pagination-and-
 * sorting.
 *
 * `fetchOnly` (used by the effect) never calls `setState` synchronously —
 * only from inside its `.then`/`.catch` — so a url change re-fetches
 * without flashing a loading state over the still-valid previous page.
 * `reload` (used by retry buttons and after mutations) resets to "loading"
 * first; it's only ever invoked from event handlers, never directly by an
 * effect, so that synchronous reset can't cascade renders. */
export function useAdminList<T>(url: string) {
  const [state, setState] = useState<ListState<T>>({ status: "loading" });

  const fetchOnly = useCallback(() => {
    fetchJson<ListResponse<T>>(url)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  }, [url]);

  useEffect(() => {
    fetchOnly();
  }, [fetchOnly]);

  const reload = useCallback(() => {
    setState({ status: "loading" });
    fetchOnly();
  }, [fetchOnly]);

  return { state, reload };
}

"use client";

/** Client-side fetch helper for the gallery's own `/api/*` routes (never the
 * backend directly — see docs/authentication.md#2). Throws with the
 * server's error message so callers can show it directly in an ErrorState. */
export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { message?: string };
    throw new Error(body.message ?? "Something went wrong. Please try again.");
  }
  return response.json() as Promise<T>;
}

/** Same error-handling as [fetchJson], for endpoints with no response body
 * (e.g. `DELETE /api/designs/search/history`, which proxies the backend's
 * `204 No Content`). */
export async function sendRequest(url: string, method: "DELETE"): Promise<void> {
  const response = await fetch(url, { method });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { message?: string };
    throw new Error(body.message ?? "Something went wrong. Please try again.");
  }
}

/** Same error-handling as [fetchJson], for mutations that send a JSON body
 * and/or return one (like/save toggles, collection CRUD) — a 204 response
 * resolves to `undefined`. */
export async function mutateJson<T>(
  url: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const responseBody = (await response.json().catch(() => ({}))) as { message?: string };
    throw new Error(responseBody.message ?? "Something went wrong. Please try again.");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

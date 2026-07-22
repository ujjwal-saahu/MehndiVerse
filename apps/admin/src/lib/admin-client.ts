"use client";

/** Client-side fetch helpers for this app's own `/api/admin/*` proxy (never
 * the backend directly) — mirrors apps/web/src/lib/gallery-client.ts. */
export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { message?: string };
    throw new Error(body.message ?? "Something went wrong. Please try again.");
  }
  return response.json() as Promise<T>;
}

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

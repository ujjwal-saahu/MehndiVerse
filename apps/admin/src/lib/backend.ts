/** Server-only helpers for talking to the FastAPI backend's `/api/v1/auth/*`
 * endpoints. Route handlers under `src/app/api/auth/` are the *only* place
 * that calls the backend directly. See docs/authentication.md#2 and #7.
 */

export function backendBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export interface BackendErrorBody {
  error?: { code: string; message: string };
  detail?: unknown;
}

export async function backendFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${backendBaseUrl()}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
}

export async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    if (body.error?.message) return body.error.message;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return String(body.detail[0].msg);
  } catch {
    // fall through to generic message
  }
  return "Something went wrong. Please try again.";
}

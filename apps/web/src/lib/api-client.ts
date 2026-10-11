// Shared request helper for the pages added on Day 41: same-origin cookie session, typed
// JSON and errors that keep the HTTP status and Retry-After for the existing notices.
import { parseRetryAfter } from "../components/rate-limit-notice";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`) as Error & { status?: number; retryAfter?: number };
    error.status = response.status;
    error.retryAfter = parseRetryAfter(response.headers.get("Retry-After"));
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function httpStatus(error: unknown): number | undefined {
  return error instanceof Error ? (error as Error & { status?: number }).status : undefined;
}

export function isAbort(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

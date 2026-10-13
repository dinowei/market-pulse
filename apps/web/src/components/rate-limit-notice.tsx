"use client";

export function isRateLimited(error: unknown): boolean {
  return error instanceof Error && (error as Error & { status?: number }).status === 429;
}

export function retryAfterSeconds(error: unknown): number | undefined {
  const value = error instanceof Error ? (error as Error & { retryAfter?: number }).retryAfter : undefined;
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : undefined;
}

export function parseRetryAfter(header: string | null): number | undefined {
  return header !== null && /^\d{1,5}$/.test(header.trim()) && Number(header) > 0 ? Number(header) : undefined;
}

export function rateLimitMessage(retryAfter?: number): string {
  return retryAfter === undefined
    ? "Muitas requisições, aguarde alguns segundos."
    : `Muitas requisições, aguarde ${retryAfter} segundos.`;
}

export function RateLimitNotice({ retryAfter, onRetry }: { retryAfter?: number; onRetry: () => void }) {
  return (
    <div className="state-note" role="alert">
      <p>{rateLimitMessage(retryAfter)}</p>
      <button type="button" onClick={onRetry}>Tentar novamente</button>
    </div>
  );
}

export type ApiRewrite = { source: string; destination: string };

/**
 * Same-origin proxy for /api/v1 (ADR-008). Unset means no proxy (local development).
 * A set value must be a bare https origin, so a typo fails the build instead of
 * silently sending session cookies to an unexpected host or over plain HTTP.
 */
export function apiProxyRewrites(rawOrigin: string | undefined): ApiRewrite[] {
  const value = rawOrigin?.trim();
  if (!value) return [];

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("MARKET_PULSE_API_PROXY_ORIGIN must be an absolute https origin");
  }
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) {
    throw new Error("MARKET_PULSE_API_PROXY_ORIGIN must be an absolute https origin");
  }
  if (url.pathname !== "/") {
    throw new Error("MARKET_PULSE_API_PROXY_ORIGIN must not contain a path");
  }

  return [{ source: "/api/v1/:path*", destination: `${url.origin}/api/v1/:path*` }];
}

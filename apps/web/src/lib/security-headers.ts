/** Observation-only frontend CSP. No endpoint receives or stores violation reports. */
export const FRONTEND_CSP_REPORT_ONLY_RULE = {
  source: "/:path*",
  headers: [
    {
      key: "Content-Security-Policy-Report-Only",
      value: "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'",
    },
  ],
};

import type { NextConfig } from "next";

import { apiProxyRewrites } from "./src/lib/api-proxy";
import { FRONTEND_CSP_REPORT_ONLY_RULE } from "./src/lib/security-headers";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Governance is maintained explicitly, not rewritten by each local demo run.
  agentRules: false,
  // ADR-008: in staging/production the browser talks only to the web origin, so the
  // session cookie stays first-party; local development keeps calling the API directly.
  async rewrites() {
    return apiProxyRewrites(process.env.MARKET_PULSE_API_PROXY_ORIGIN);
  },
  // H-02: observation only. The theme boot script is inline, so this policy must be
  // reviewed in a browser before any future enforced CSP is considered. No report
  // collector is configured, avoiding server-side storage of request details.
  async headers() {
    return [FRONTEND_CSP_REPORT_ONLY_RULE];
  },
};

export default nextConfig;

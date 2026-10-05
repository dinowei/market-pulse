import type { NextConfig } from "next";

import { apiProxyRewrites } from "./src/lib/api-proxy";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Governance is maintained explicitly, not rewritten by each local demo run.
  agentRules: false,
  // ADR-008: in staging/production the browser talks only to the web origin, so the
  // session cookie stays first-party; local development keeps calling the API directly.
  async rewrites() {
    return apiProxyRewrites(process.env.MARKET_PULSE_API_PROXY_ORIGIN);
  },
};

export default nextConfig;

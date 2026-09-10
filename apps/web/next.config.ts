import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Governance is maintained explicitly, not rewritten by each local demo run.
  agentRules: false,
};

export default nextConfig;

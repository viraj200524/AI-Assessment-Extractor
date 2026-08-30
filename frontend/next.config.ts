import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output bundle when building container images
  ...(process.env.NEXT_OUTPUT_STANDALONE === "1" ? { output: "standalone" as const } : {}),
};

export default nextConfig;

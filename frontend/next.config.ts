import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone emits a self-contained server bundle at .next/standalone, which
  // Dockerfile.vercel copies into its runtime stage. Opt-in via env because tracing the
  // dependency tree creates symlinks, which fails on Windows without Developer Mode or an
  // elevated shell. `next dev`, `next build`, and Vercel's native build are unaffected.
  ...(process.env.NEXT_OUTPUT_STANDALONE === "1" ? { output: "standalone" as const } : {}),
};

export default nextConfig;

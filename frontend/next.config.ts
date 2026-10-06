import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Vercel uses its own output; standalone is for container self-hosting.
  ...(process.env.VERCEL ? {} : { output: "standalone" as const }),
};

export default nextConfig;

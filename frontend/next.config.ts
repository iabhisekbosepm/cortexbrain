import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // API_INTERNAL_URL is server-only (Docker: http://cortexbrain:8000)
    // NEXT_PUBLIC_API_URL is client-facing (browser: http://localhost:8000)
    const backendUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  experimental: {
    proxyTimeout: 300_000, // 5 minutes — cognify can take a while on large docs
  },
};

export default nextConfig;

import type { NextConfig } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH?.replace(/\/$/, "") || undefined;

const nextConfig: NextConfig = {
  basePath,
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;

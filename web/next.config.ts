import type { NextConfig } from "next";
const api = process.env.NEXUS_API ?? "http://127.0.0.1:8000";
const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
export default config;

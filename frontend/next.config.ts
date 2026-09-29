import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /*
   * A static export: the console is HTML on S3 behind CloudFront, with no
   * server of its own. Every page loads its data from the browser through
   * /api on the same domain - see src/lib/page-data.tsx - and dynamic routes
   * are one placeholder page each, which CloudFront serves for every real id
   * (the rewrite function in template.yaml).
   */
  output: "export",
  // S3 serves keys; trailing-slash URLs map onto path/index.html, which is
  // what the CloudFront rewrite assumes.
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;

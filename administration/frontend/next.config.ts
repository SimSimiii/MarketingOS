import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /*
   * A static export, and deliberately.
   *
   * The console has no server of its own: it is HTML on S3 behind CloudFront,
   * talking to the admin Lambda over CORS with a bearer token. That means no
   * second runtime to keep patched, no origin to secure, and nothing between
   * the operator and the API that could hold a session it should not.
   *
   * The cost is that every page is a client component and deep links need an
   * edge rewrite - see AdminUrlRewriteFunction in the SAM template.
   */
  output: "export",
  // S3 serves keys; trailing-slash URLs map cleanly onto path/index.html,
  // which is what the CloudFront rewrite assumes.
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;

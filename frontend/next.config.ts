import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /*
   * `standalone` emits `.next/standalone` - the server plus only the
   * node_modules it actually reaches - which is what the Lambda container
   * image copies. Without it the image would carry the whole dependency tree,
   * most of it build-time tooling.
   *
   * It changes nothing about `next dev` or the normal `.next` output, so a
   * laptop is unaffected.
   */
  output: "standalone",
};

export default nextConfig;

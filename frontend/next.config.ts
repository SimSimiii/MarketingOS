import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function config(phase: string): NextConfig {
  return {
    /*
     * A static export: the console is HTML on S3 behind CloudFront, with no
     * server of its own. Every page loads its data from the browser through
     * /api on the same domain - see src/lib/page-data.tsx - and dynamic routes
     * are one placeholder page each, which CloudFront serves for every real id
     * (the rewrite function in template.yaml).
     *
     * Not under `next dev`, though. There is no CloudFront rewrite in front of
     * the dev server, so the address bar holds a real id, and in export mode
     * Next refuses any param `generateStaticParams` did not list: every brand,
     * campaign and run page answered 500. Without `output` the dev server
     * renders the same page for any id, which is what the rewrite does in
     * production. `next build` still exports, so what ships is unchanged.
     */
    output: phase === PHASE_DEVELOPMENT_SERVER ? undefined : "export",
    // S3 serves keys; trailing-slash URLs map onto path/index.html, which is
    // what the CloudFront rewrite assumes.
    trailingSlash: true,
    images: { unoptimized: true },
  };
}

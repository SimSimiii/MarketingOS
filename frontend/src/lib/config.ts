const PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api";

/** Where the API is, from wherever this code is running.
 *
 * On AWS the browser calls "/api" - the console's own domain, which CloudFront
 * routes to API Gateway - so the bundle names no domain and needs no CORS. A
 * server has no page for "/api" to be relative to, so the server side reads
 * API_INTERNAL_URL instead: API Gateway's own address, set at runtime by
 * frontend/template.yaml. It is not NEXT_PUBLIC_, so it never reaches the
 * browser. Unset (a laptop), both sides use NEXT_PUBLIC_API_URL as before.
 */
export const API_URL =
  typeof window === "undefined"
    ? (process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? PUBLIC_API_URL)
    : PUBLIC_API_URL;

/** Whether this deployment has accounts at all.
 *
 * Mirrors the API's own AUTH_REQUIRED. It has to be a build-time flag rather
 * than something fetched, because `src/proxy.ts` reads it on every request and
 * Next is explicit that the proxy is not the place for data fetching.
 *
 * The default is false, matching the API: a laptop install keeps the
 * single-workspace shape the product had before accounts existed, with no
 * sign-in page in the way. Production sets it to "true" at build time - see
 * frontend/buildspec.yml.
 */
export const AUTH_REQUIRED = process.env.NEXT_PUBLIC_AUTH_REQUIRED === "true";

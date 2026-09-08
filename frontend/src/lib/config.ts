export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api";

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

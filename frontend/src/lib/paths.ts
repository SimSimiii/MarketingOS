/** The path without its trailing slash, "/" for the root.
 *
 * The console is exported with `trailingSlash: true`, so the address bar says
 * "/campaigns/" where route constants say "/campaigns". Anything that compares
 * a pathname against a route goes through this first - comparing the raw one
 * made the sign-in page render inside the full app shell, and the exported HTML
 * disagree with the browser's first render. */
export function normalizePath(pathname: string): string {
  return pathname.replace(/\/+$/, "") || "/";
}

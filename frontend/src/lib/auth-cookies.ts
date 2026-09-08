/**
 * The two cookie names, in one place.
 *
 * They are read by four things that cannot import each other - the browser
 * client, the server client, the route handlers and the middleware - so the
 * names live in a module with no imports of its own. A typo here used to mean
 * "signed in everywhere except the one page that checks".
 *
 * `ACCESS_TOKEN_COOKIE` also has to match `app.auth.dependencies` on the API
 * side, which reads the same name as a fallback to the Authorization header.
 */

export const ACCESS_TOKEN_COOKIE = "mos_access_token";

/** httpOnly and scoped to `/api/auth`, so it is sent only to the route
 * handlers that mint access tokens from it and to nothing else. */
export const REFRESH_TOKEN_COOKIE = "mos_refresh_token";
export const REFRESH_COOKIE_PATH = "/api/auth";

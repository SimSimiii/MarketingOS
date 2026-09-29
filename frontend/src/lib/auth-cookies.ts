/**
 * The access token cookie's name. The API sets it (backend/app/api/routes/
 * auth.py) and `app.auth.dependencies` reads the same name as a fallback to
 * the Authorization header; this side reads it to send that header.
 *
 * The refresh token cookie is httpOnly and scoped to /api/auth, so nothing on
 * this side ever reads it - it is only ever sent back to the API.
 */

export const ACCESS_TOKEN_COOKIE = "mos_access_token";

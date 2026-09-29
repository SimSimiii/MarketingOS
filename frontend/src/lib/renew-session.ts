import { ACCESS_TOKEN_COOKIE } from "./auth-cookies";
import { API_URL } from "./config";

let pending: Promise<boolean> | undefined;

function token(): string | undefined {
  return document.cookie.split("; ").find(row => row.startsWith(`${ACCESS_TOKEN_COOKIE}=`));
}

/** One refresh per browser, including concurrent requests in different tabs. */
export function renewSession(): Promise<boolean> {
  if (pending) return pending;
  const previous = token();
  async function renew() {
    if (token() && token() !== previous) return true;
    // The refresh token is the httpOnly cookie scoped to /api/auth; the body
    // is empty because the API reads the cookie when the body has no token.
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (response.status >= 500) throw new Error("Session service unavailable. Please retry.");
    return response.ok;
  }
  pending = Promise.resolve(navigator.locks ? navigator.locks.request("marketingos-refresh", renew) : renew())
    .finally(() => { pending = undefined; });
  return pending;
}

import { ACCESS_TOKEN_COOKIE } from "./auth-cookies";

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
    const response = await fetch("/bff/auth/refresh", { method: "POST", credentials: "same-origin" });
    if (response.status >= 500) throw new Error("Session service unavailable. Please retry.");
    return response.ok;
  }
  pending = Promise.resolve(navigator.locks ? navigator.locks.request("marketingos-refresh", renew) : renew())
    .finally(() => { pending = undefined; });
  return pending;
}

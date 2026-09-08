"use client";

/**
 * Who is signed in, resolved once per page load.
 *
 * The token in sessionStorage is not proof of anything by itself - it may be
 * expired, and the operator behind it may have been deactivated since. So the
 * provider asks `/api/auth/me` on mount and treats that answer, not the
 * stored string, as the session. It is one request, and it is what stops the
 * console rendering a full back-office around a credential the API will
 * refuse.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import { api, readToken, writeToken, type Admin } from "@/lib/api";

interface Session {
  admin: Admin | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    if (!readToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((me) => {
        if (!cancelled) setAdmin(me);
      })
      .catch(() => {
        // `request` has already dropped the token on a 401.
        if (!cancelled) setAdmin(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    writeToken(result.access_token);
    setAdmin(result.admin);
  }, []);

  const signOut = useCallback(async () => {
    // Best-effort: the row it writes is for the audit trail, and a network
    // failure must not leave somebody stuck signed in.
    await api.logout().catch(() => undefined);
    writeToken(null);
    setAdmin(null);
    router.replace("/login/");
  }, [router]);

  const value = useMemo(
    () => ({ admin, loading, signIn, signOut }),
    [admin, loading, signIn, signOut],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const context = useContext(SessionContext);
  if (context === null) throw new Error("useSession must be used inside SessionProvider");
  return context;
}

/**
 * Send an unauthenticated visitor to the sign-in page.
 *
 * A convenience, not a control: everything worth protecting is behind the
 * API, which checks the token on every call. This only stops the console from
 * rendering empty tables and a row of failed requests.
 */
export function useRequireSession(): Session {
  const session = useSession();
  const router = useRouter();
  useEffect(() => {
    if (!session.loading && session.admin === null) router.replace("/login/");
  }, [session.loading, session.admin, router]);
  return session;
}

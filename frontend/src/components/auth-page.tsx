"use client";

import { useEffect, useState } from "react";

import { AuthForm } from "@/components/auth-form";
import { api } from "@/lib/api-client";

/**
 * Whether to offer a "create one" link is the API's answer, not a guess.
 *
 * `/auth/config` is the one unauthenticated endpoint, and it exists for this:
 * a closed deployment should not show a signup link that answers 403 when
 * somebody follows it. If the API is unreachable the form still renders -
 * being unable to describe the deployment is not a reason to withhold the
 * only page a signed-out visitor can use.
 */
export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const [allowSignup, setAllowSignup] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .getAuthConfig()
      .then((config) => {
        if (active) setAllowSignup(config.allow_public_signup);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  return <AuthForm mode={mode} allowSignup={allowSignup} />;
}

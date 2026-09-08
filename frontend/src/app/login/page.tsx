import { Suspense } from "react";
import type { Metadata } from "next";

import { api } from "@/lib/api-server";
import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "Sign in · MarketingOS" };

/**
 * Whether to offer a "create one" link is the API's answer, not a guess.
 *
 * `/auth/config` is the one unauthenticated endpoint, and it exists for this:
 * a closed deployment should not show a signup link that answers 403 when
 * somebody follows it. If the API is unreachable the form still renders -
 * being unable to describe the deployment is not a reason to withhold the
 * only page a signed-out visitor can use.
 */
export default async function LoginPage() {
  const config = await api.getAuthConfig().catch(() => null);
  return (
    <Suspense>
      <AuthForm mode="login" allowSignup={config?.allow_public_signup ?? false} />
    </Suspense>
  );
}

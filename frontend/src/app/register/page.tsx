import { Suspense } from "react";
import type { Metadata } from "next";

import { api } from "@/lib/api-server";
import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "Create an account · MarketingOS" };

export default async function RegisterPage() {
  const config = await api.getAuthConfig().catch(() => null);
  // Rendered even where signup is closed, rather than 404ing: somebody who
  // followed a stale link deserves a sentence explaining why, and the form
  // itself says so before they type anything.
  return (
    <Suspense>
      <AuthForm mode="register" allowSignup={config?.allow_public_signup ?? false} />
    </Suspense>
  );
}

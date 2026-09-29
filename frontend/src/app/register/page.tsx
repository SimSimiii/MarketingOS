import { Suspense } from "react";
import type { Metadata } from "next";

import { AuthPage } from "@/components/auth-page";

export const metadata: Metadata = { title: "Create an account · MarketingOS" };

// Rendered even where signup is closed, rather than 404ing: somebody who
// followed a stale link deserves a sentence explaining why, and the form
// itself says so before they type anything.
export default function RegisterPage() {
  return (
    <Suspense>
      <AuthPage mode="register" />
    </Suspense>
  );
}

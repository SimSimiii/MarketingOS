import type { Metadata } from "next";

import { SessionProvider } from "@/lib/session";
import "./globals.css";

export const metadata: Metadata = {
  title: "MarketingOS — back-office",
  description: "Accounts, plans and the audit trail.",
  // The console is not something a search engine should index, and a static
  // export has no server to send the header from.
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-dvh">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}

"use client";

import { useEffect, useState } from "react";
import { renewSession } from "@/lib/renew-session";

export default function RenewSessionPage() {
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const requested = new URLSearchParams(window.location.search).get("next") || "/";
    const next = requested.startsWith("/") && !requested.startsWith("//") && !requested.includes("\\")
      && !requested.startsWith("/session/renew") ? requested : "/";
    void renewSession().then(ok => {
      if (active) window.location.replace(ok ? next : `/login?next=${encodeURIComponent(next)}`);
    }).catch(() => { if (active) setError("Connexion momentanément indisponible."); });
    return () => { active = false; };
  }, []);
  return <main className="p-8"><p>{error || "Renouvellement de votre session…"}</p>
    {error && <button onClick={() => window.location.reload()}>Réessayer</button>}</main>;
}

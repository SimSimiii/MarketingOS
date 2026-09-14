"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { CompilationStatus } from "@/lib/types";

export function CompileButton({ brandId, compiled }: { brandId: string; compiled: boolean }) {
  const router = useRouter();
  const [job, setJob] = useState<CompilationStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const wasRunning = useRef(false);

  const [refreshing, setRefreshing] = useState(true);
  const refreshStatus = useCallback(async () => {
    try {
      const status = await api.getKnowledgeCompilation(brandId);
      setJob(status);
      setPollError("");
      if (wasRunning.current && status.state === "completed") router.refresh();
      wasRunning.current = status.state === "running";
    } catch (err) { setPollError(err instanceof Error ? err.message : "Unable to check compilation."); }
    finally { setRefreshing(false); }
  }, [brandId, router]);
  useEffect(() => {
    let cancelled = false;
    api.getKnowledgeCompilation(brandId).then((status) => {
      if (cancelled) return;
      setJob(status);
      wasRunning.current = status.state === "running";
    }).catch((err) => {
      if (!cancelled) setPollError(err instanceof Error ? err.message : "Unable to check compilation.");
    }).finally(() => { if (!cancelled) setRefreshing(false); });
    return () => { cancelled = true; };
  }, [brandId]);

  async function compile() {
    setStarting(true);
    setError("");
    try {
      const status = await api.compileKnowledge(brandId);
      wasRunning.current = status.state === "running";
      setJob(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compilation could not start.");
    } finally {
      setStarting(false);
    }
  }

  const busy = starting || job?.state === "running";
  return (
    <div className="space-y-2">
      <Button variant="outline" size="sm" disabled={refreshing} onClick={async () => { setRefreshing(true); await refreshStatus(); }}>{refreshing ? "Refreshing..." : "Refresh status"}</Button>
      <Button onClick={compile} disabled={busy || refreshing || job === null} size="sm">
        {busy ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
        {busy ? "Compiling…" : compiled ? "Recompile knowledge sources" : "Compile knowledge sources"}
      </Button>
      <p className="text-xs text-muted-foreground">Reads all attached sources using your model subscription.</p>
      {job?.message && <p role="status" className="text-sm text-muted-foreground">{job.message}</p>}
      {job?.state === "running" && (
        <Link href="/live" className="inline-block text-sm text-violet-300 hover:underline">Follow in Runs →</Link>
      )}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {pollError && <p role="alert" className="text-sm text-destructive">{pollError}</p>}
    </div>
  );
}

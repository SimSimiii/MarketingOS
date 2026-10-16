"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { CompilationStatus } from "@/lib/types";
import { refreshPage } from "@/lib/page-data";
import { problemText, progressText } from "@/lib/product-progress";

export function CompileButton({ brandId, compiled }: { brandId: string; compiled: boolean }) {
  const [job, setJob] = useState<CompilationStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const wasRunning = useRef(false);

  const [refreshing, setRefreshing] = useState(true);
  const refreshStatus = useCallback(async () => {
    api.invalidate();
    try {
      const status = await api.getKnowledgeCompilation(brandId);
      setJob(status);
      setPollError("");
      if (wasRunning.current && status.state === "completed") refreshPage();
      wasRunning.current = status.state === "running";
    } catch (err) { setPollError(err instanceof Error ? err.message : "Unable to check compilation."); }
    finally { setRefreshing(false); }
  }, [brandId]);
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
    <div className="space-y-2.5">
      {/* Side by side: they were two inline buttons in a stacked block, so the
          second sat half a line lower than the first. */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={refreshing}
          onClick={async () => { setRefreshing(true); await refreshStatus(); }}
        >
          <RefreshCw className={refreshing ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
          {refreshing ? "Refreshing…" : "Refresh status"}
        </Button>
        <Button onClick={compile} disabled={busy || refreshing || job === null} size="sm">
          {busy ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
          {busy ? "Compiling…" : compiled ? "Recompile sources" : "Compile sources"}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">Reads all attached sources to prepare your brand knowledge.</p>
      {job?.message && (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          {job.state === "running" && <span className="live-dot" aria-hidden="true" />}
          {job.state === "failed" ? problemText(job.message) : progressText(job.message, "Preparing your brand knowledge…")}
        </p>
      )}
      {job?.state === "running" && (
        <Link href="/live" className="inline-block text-sm font-medium text-violet-300 hover:text-violet-200">Follow in Runs →</Link>
      )}
      {error && <p role="alert" className="text-sm text-red-300">{problemText(error)}</p>}
      {pollError && <p role="alert" className="text-sm text-red-300">{problemText(pollError)}</p>}
    </div>
  );
}

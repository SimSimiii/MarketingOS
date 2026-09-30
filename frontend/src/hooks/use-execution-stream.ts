"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import type { LiveExecutionEvent } from "@/lib/types";
import { formatTime } from "@/lib/format";
/** Persisted snapshots only: no open connection and no automatic polling. */
export function useExecutionStream(executionId: string) {
  const [events, setEvents] = useState<LiveExecutionEvent[]>([]);
  const [phase, setPhase] = useState<"loading" | "ready" | "error">("loading");
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const generation = useRef(0);
  const load = useCallback(async () => {
    const current = ++generation.current;
    try {
      const timeline = await api.getExecutionTimeline(executionId);
      if (current !== generation.current) return;
      setEvents(timeline.events);
      setUpdatedAt(formatTime(Date.now()));
      setPhase("ready");
    } catch {
      if (current === generation.current) setPhase("error");
    }
  }, [executionId]);
  useEffect(() => {
    const current = ++generation.current;
    let cancelled = false;
    api.getExecutionTimeline(executionId).then((timeline) => {
      if (cancelled || current !== generation.current) return;
      setEvents(timeline.events);
      setUpdatedAt(formatTime(Date.now()));
      setPhase("ready");
    }).catch(() => {
      if (!cancelled && current === generation.current) setPhase("error");
    });
    return () => { cancelled = true; };
  }, [executionId]);
  const refresh = useCallback(async () => {
    setPhase("loading");
    api.invalidate();
    await load();
  }, [load]);
  return { events, phase, refresh, updatedAt };
}

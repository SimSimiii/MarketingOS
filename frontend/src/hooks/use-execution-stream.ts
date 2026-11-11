"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import type { LiveExecutionEvent } from "@/lib/types";
import { formatTime } from "@/lib/format";
/** Poll saved snapshots while a run is active. */
export function useExecutionStream(executionId: string, initiallyLive: boolean) {
  const [events, setEvents] = useState<LiveExecutionEvent[]>([]);
  const [phase, setPhase] = useState<"loading" | "ready" | "error">("loading");
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const generation = useRef(0);
  const load = useCallback(async (active: () => boolean = () => true) => {
    const current = ++generation.current;
    try {
      const timeline = await api.getExecutionTimeline(executionId);
      if (!active() || current !== generation.current) return;
      setEvents(timeline.events);
      setUpdatedAt(formatTime(Date.now()));
      setPhase("ready");
      return timeline.events.some((event) => event.type === "execution_finished");
    } catch {
      if (active() && current === generation.current) setPhase("error");
    }
  }, [executionId]);
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      const finished = await load(() => !cancelled);
      if (!cancelled && initiallyLive && !finished) timer = setTimeout(poll, 5000);
    }
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [initiallyLive, load]);
  const refresh = useCallback(async () => {
    setPhase("loading");
    api.invalidate();
    await load();
  }, [load]);
  return { events, phase, refresh, updatedAt };
}

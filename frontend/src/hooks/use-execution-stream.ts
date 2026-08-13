"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api-client";
import type { LiveExecutionEvent } from "@/lib/types";

export type StreamPhase = "loading" | "live" | "reconnecting" | "closed";

export interface ExecutionStream {
  events: LiveExecutionEvent[];
  phase: StreamPhase;
}

/** Watch one execution: everything that already happened, then everything
 * that happens next.
 *
 * The history is loaded over HTTP first and the stream is opened from the
 * position it ended at, so a page that was opened late - or simply
 * reloaded - shows the whole run instead of starting blank. The browser's
 * own SSE reconnection carries `Last-Event-ID`, so a dropped connection
 * resumes at the right place too.
 */
export function useExecutionStream(executionId: string, live: boolean): ExecutionStream {
  const [events, setEvents] = useState<LiveExecutionEvent[]>([]);
  const [phase, setPhase] = useState<StreamPhase>("loading");
  // Guards against a late history response overwriting events that already
  // arrived on the stream, and against React 18+ double-invoked effects.
  const generation = useRef(0);

  useEffect(() => {
    const current = ++generation.current;
    let source: EventSource | null = null;
    let cancelled = false;

    async function start() {
      let resumeFrom = 0;
      try {
        const timeline = await api.getExecutionTimeline(executionId);
        if (cancelled || current !== generation.current) return;
        setEvents(timeline.events);
        resumeFrom = timeline.last_event_id;
      } catch {
        // A history that will not load is not a reason to miss what happens
        // next - fall through and watch from here.
      }
      if (cancelled || current !== generation.current) return;

      if (!live) {
        setPhase("closed");
        return;
      }

      source = new EventSource(api.executionStreamUrl(executionId, resumeFrom));
      setPhase("live");

      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as LiveExecutionEvent;
        setPhase("live");
        setEvents((previous) => [...previous, event]);
        if (event.type === "execution_finished") {
          source?.close();
          setPhase("closed");
        }
      };

      source.onerror = () => {
        // The browser retries on its own and resends Last-Event-ID; say so
        // rather than leaving a "live" badge on a dead connection.
        if (source?.readyState === EventSource.CLOSED) {
          setPhase("closed");
        } else {
          setPhase("reconnecting");
        }
      };
    }

    void start();

    return () => {
      cancelled = true;
      source?.close();
    };
  }, [executionId, live]);

  return { events, phase };
}

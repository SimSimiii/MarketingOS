/** Poll after completion, pause in background tabs, and refresh on return.
 * The callback handles its own errors; disposal prevents any new work.
 */
export function startVisiblePolling(
  refresh: () => Promise<void>,
  intervalMs: number,
  visibility: Pick<Document, "hidden" | "addEventListener" | "removeEventListener"> = document,
): () => void {
  let stopped = false;
  let pending = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function run() {
    if (stopped || pending || visibility.hidden) return;
    pending = true;
    try {
      await refresh();
    } finally {
      pending = false;
      if (!stopped && !visibility.hidden) timer = setTimeout(() => { void run(); }, intervalMs);
    }
  }

  function onVisibilityChange() {
    clearTimeout(timer);
    if (!visibility.hidden) void run();
  }

  visibility.addEventListener("visibilitychange", onVisibilityChange);
  if (!visibility.hidden) timer = setTimeout(() => { void run(); }, intervalMs);
  return () => {
    stopped = true;
    clearTimeout(timer);
    visibility.removeEventListener("visibilitychange", onVisibilityChange);
  };
}

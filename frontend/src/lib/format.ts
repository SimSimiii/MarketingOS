const UNITS: [limit: number, seconds: number, name: Intl.RelativeTimeFormatUnit][] = [
  [60, 1, "second"],
  [3600, 60, "minute"],
  [86400, 3600, "hour"],
  [604800, 86400, "day"],
  [2592000, 604800, "week"],
  [31536000, 2592000, "month"],
  [Infinity, 31536000, "year"],
];

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

/** "2 minutes ago" - pair it with the absolute timestamp in a `title`. */
export function timeAgo(iso: string, now: number = Date.now()): string {
  const elapsedSeconds = (new Date(iso).getTime() - now) / 1000;
  const magnitude = Math.abs(elapsedSeconds);
  for (const [limit, secondsPerUnit, unit] of UNITS) {
    if (magnitude < limit) {
      return relative.format(Math.round(elapsedSeconds / secondsPerUnit), unit);
    }
  }
  return new Date(iso).toLocaleDateString();
}

export function formatAbsolute(iso: string): string {
  return new Date(iso).toLocaleString();
}

/** Elapsed wall time as m:ss (or h:mm:ss past an hour). */
export function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const seconds = totalSeconds % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const paddedSeconds = String(seconds).padStart(2, "0");
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${paddedSeconds}`;
  }
  return `${minutes}:${paddedSeconds}`;
}

export function formatTokens(count: number): string {
  if (count < 1000) return String(count);
  return `${(count / 1000).toFixed(count < 10_000 ? 1 : 0)}k`;
}

/** Sub-cent spend still deserves a number rather than "$0.00". */
export function formatCost(usd: number): string {
  if (usd <= 0) return "—";
  return usd < 0.01 ? `<$0.01` : `$${usd.toFixed(2)}`;
}

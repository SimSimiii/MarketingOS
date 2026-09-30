const UNITS: [limit: number, seconds: number, name: Intl.RelativeTimeFormatUnit][] = [
  [60, 1, "second"],
  [3600, 60, "minute"],
  [86400, 3600, "hour"],
  [604800, 86400, "day"],
  [2592000, 604800, "week"],
  [31536000, 2592000, "month"],
  [Infinity, 31536000, "year"],
];

/** The console is written in English, so its dates are too. Leaving the
 * locale to the browser printed "avant-hier" and "il y a 2 semaines" beside
 * English labels for anyone whose system is set to French - one sentence in
 * two languages. British English for day-first dates, which is also what most
 * of the people outside the US reading this expect. */
export const LOCALE = "en-GB";

const relative = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });
const absolute = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeStyle: "short" });
const dayOnly = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium" });
const clock = new Intl.DateTimeFormat(LOCALE, { timeStyle: "medium" });
const integer = new Intl.NumberFormat(LOCALE);

/** "2 minutes ago" - pair it with the absolute timestamp in a `title`. */
export function timeAgo(iso: string, now: number = Date.now()): string {
  const elapsedSeconds = (new Date(iso).getTime() - now) / 1000;
  const magnitude = Math.abs(elapsedSeconds);
  for (const [limit, secondsPerUnit, unit] of UNITS) {
    if (magnitude < limit) {
      return relative.format(Math.round(elapsedSeconds / secondsPerUnit), unit);
    }
  }
  return formatDate(iso);
}

/** "30 Sept 2026, 01:26" - for a `title`, or wherever the exact moment matters. */
export function formatAbsolute(iso: string): string {
  return absolute.format(new Date(iso));
}

/** "30 Sept 2026". */
export function formatDate(iso: string): string {
  return dayOnly.format(new Date(iso));
}

/** "01:26:08" - a time of day, from an ISO string or epoch milliseconds. */
export function formatTime(when: string | number): string {
  return clock.format(new Date(when));
}

/** "17,897" - a count with the separators the rest of the page uses. */
export function formatNumber(value: number): string {
  return integer.format(value);
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

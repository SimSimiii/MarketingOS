"""Estimate how much of the current 5-hour Claude usage window has been spent.

There is no API, CLI subcommand or local file that reports *remaining* quota. The
only place a number appears is in the 429 payload itself, and only once you have
already hit the wall. So this reads what is actually recorded — the `usage` block
on every assistant message in every session transcript — and reports CONSUMPTION.

Two things make that useful anyway:

1. The 5-hour window is rolling from first use, not wall-clock. Sessions separated
   by a gap of 5h or more are in different windows, so the window boundary is
   recoverable from the timestamps alone.
2. Every 429 recorded in a transcript is a calibration point: the consumption at
   that moment WAS the ceiling, for that plan, that window. Enough of them and the
   ceiling stops being a guess. `--calibrate` prints the ones already on disk.

Usage:
    python quota.py              # current window: spent, elapsed, time left
    python quota.py --json       # same, machine-readable
    python quota.py --calibrate  # every observed rate-limit event and its ceiling
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

WINDOW = timedelta(hours=5)
PROJECTS = Path.home() / ".claude" / "projects"

#: Cache reads are billed at a fraction of fresh input. The exact multiplier for a
#: subscription plan is not published, so this is a stated assumption rather than a
#: fact — it only affects the single "weighted" figure, never the raw components.
CACHE_READ_WEIGHT = 0.1


@dataclass
class Call:
    at: datetime
    fresh_in: int
    cache_write: int
    cache_read: int
    out: int

    @property
    def raw(self) -> int:
        return self.fresh_in + self.cache_write + self.cache_read + self.out

    @property
    def weighted(self) -> int:
        return int(
            self.fresh_in
            + self.cache_write
            + self.cache_read * CACHE_READ_WEIGHT
            + self.out
        )


def _parse(line: str) -> tuple[Call | None, dict | None]:
    """One transcript line -> (a model call, a rate-limit event). Either may be None."""
    if '"usage"' not in line and '"quotaLimits"' not in line:
        return None, None
    try:
        row = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None, None
    if not isinstance(row, dict):
        return None, None

    stamp = row.get("timestamp")
    at = None
    if isinstance(stamp, str):
        try:
            at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            at = None

    limits = row.get("quotaLimits")
    event = None
    if isinstance(limits, dict) and at is not None:
        event = {"at": at, **limits}

    call = None
    message = row.get("message")
    if isinstance(message, dict) and at is not None:
        usage = message.get("usage")
        if isinstance(usage, dict):
            call = Call(
                at=at,
                fresh_in=int(usage.get("input_tokens") or 0),
                cache_write=int(usage.get("cache_creation_input_tokens") or 0),
                cache_read=int(usage.get("cache_read_input_tokens") or 0),
                out=int(usage.get("output_tokens") or 0),
            )
    return call, event


def collect() -> tuple[list[Call], list[dict]]:
    calls: list[Call] = []
    events: list[dict] = []
    if not PROJECTS.is_dir():
        return calls, events
    for path in PROJECTS.rglob("*.jsonl"):
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    call, event = _parse(line)
                    if call is not None:
                        calls.append(call)
                    if event is not None:
                        events.append(event)
        except OSError:
            continue
    calls.sort(key=lambda c: c.at)
    events.sort(key=lambda e: e["at"])
    return calls, events


def window_start(calls: list[Call], now: datetime) -> datetime | None:
    """First call of the window currently in force, or None if none is open.

    Windows are rolling from first use: a call opens a window, that window runs
    five hours, and the next call after it expires opens a fresh one.
    """
    start = None
    for call in calls:
        if start is None or call.at - start >= WINDOW:
            start = call.at
    if start is None or now - start >= WINDOW:
        return None
    return start


def summarize(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    calls, events = collect()
    start = window_start(calls, now)

    if start is None:
        return {
            "window_open": False,
            "spent_weighted": 0,
            "spent_raw": 0,
            "calls": 0,
            "note": "No window open - the next call starts a fresh five hours.",
        }

    current = [c for c in calls if start <= c.at < start + WINDOW]
    ends = start + WINDOW
    spent_weighted = sum(c.weighted for c in current)
    ceilings = calibrate(calls, events)
    #: The lowest ceiling ever observed is the safe one to plan against: a window
    #: that died at 9.8M proves the limit is no higher, never that it is that high.
    floor_ceiling = min((c["weighted_at_limit"] for c in ceilings), default=None)
    return {
        "window_open": True,
        "window_start": start.isoformat(),
        "window_ends": ends.isoformat(),
        "minutes_left": max(0, int((ends - now).total_seconds() // 60)),
        "calls": len(current),
        "spent_weighted": spent_weighted,
        "spent_raw": sum(c.raw for c in current),
        "fresh_in": sum(c.fresh_in for c in current),
        "cache_write": sum(c.cache_write for c in current),
        "cache_read": sum(c.cache_read for c in current),
        "out": sum(c.out for c in current),
        "observed_ceiling": floor_ceiling,
        "remaining_estimate": (
            max(0, floor_ceiling - spent_weighted) if floor_ceiling else None
        ),
        "ceiling_seen": ceilings,
    }


def calibrate(calls: list[Call], events: list[dict]) -> list[dict]:
    """What the window had consumed at each moment a rate limit actually fired."""
    out = []
    for event in events:
        if event.get("status") != "rejected":
            continue
        at = event["at"]
        start = window_start([c for c in calls if c.at <= at], at)
        if start is None:
            continue
        spent = [c for c in calls if start <= c.at <= at]
        out.append(
            {
                "at": at.isoformat(),
                "type": event.get("rateLimitType"),
                "weighted_at_limit": sum(c.weighted for c in spent),
                "raw_at_limit": sum(c.raw for c in spent),
                "calls_at_limit": len(spent),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--calibrate", action="store_true", help="observed rate-limit ceilings only"
    )
    args = parser.parse_args()

    data = summarize()

    if args.calibrate:
        seen = data.get("ceiling_seen") or []
        if args.json:
            print(json.dumps(seen, indent=2))
        elif not seen:
            print("No rate limit has been recorded on this machine yet.")
            print("The first one this workflow hits becomes the calibration point.")
        else:
            for row in seen:
                print(
                    f"{row['at']}  {row['type']:<10} "
                    f"weighted={row['weighted_at_limit']:,} "
                    f"raw={row['raw_at_limit']:,} calls={row['calls_at_limit']:,}"
                )
        return 0

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    if not data["window_open"]:
        print(data["note"])
        return 0

    print(f"Window opened   {data['window_start'][11:16]} UTC")
    print(f"Window closes   {data['window_ends'][11:16]} UTC  ({data['minutes_left']} min left)")
    print(f"Model calls     {data['calls']:,}")
    print(f"Spent (weighted){data['spent_weighted']:>12,}  <- cache reads at {CACHE_READ_WEIGHT:g}x")
    print(f"Spent (raw)     {data['spent_raw']:>12,}")
    print(
        f"  fresh in {data['fresh_in']:,} | cache write {data['cache_write']:,} "
        f"| cache read {data['cache_read']:,} | out {data['out']:,}"
    )
    ceiling = data.get("observed_ceiling")
    if ceiling:
        left = data["remaining_estimate"]
        pct = 100 * data["spent_weighted"] / ceiling
        print(f"\nObserved ceiling{ceiling:>12,}  (lowest window that actually 429'd)")
        print(f"Rough remaining {left:>12,}  ({pct:.0f}% of the window spent)")
        print(f"Confidence: {len(data['ceiling_seen'])} observed limit(s). Treat as an order of")
        print("magnitude, not a balance - the real stop condition is the 429 itself.")
    else:
        print("\nNo ceiling observed yet — consumption is known, remaining is not.")
        print("Run until the 429 lands; it calibrates every later run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Spawning subprocesses from an event loop that cannot, on Windows.

Both providers reach their vendor by running a CLI as a subprocess, and on
Windows only `ProactorEventLoop` can start one. Uvicorn hands its worker a
`SelectorEventLoop` whenever it spawns one (`--reload`, `--workers`), which is
exactly how this API gets run - so every provider needs the same bridge and
they must share it. Two providers each building their own thread would mean
two IOCP loops alive for the life of the process, for no reason.

Extracted from `claude_provider`, where it was written; the behaviour is
unchanged.
"""

import asyncio
import sys
import threading
from collections.abc import Callable, Coroutine
from typing import Any


def _needs_proactor_thread() -> bool:
    """True when the running loop cannot spawn the CLI subprocess.

    On Windows only `ProactorEventLoop` supports subprocesses; a
    `SelectorEventLoop` raises a bare `NotImplementedError`, which a vendor SDK
    surfaces as a message-less start failure.
    """
    if sys.platform != "win32":
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    proactor = getattr(asyncio, "ProactorEventLoop", None)
    return proactor is not None and not isinstance(loop, proactor)


def _run_in_proactor_loop[T](factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Run one coroutine on a private ProactorEventLoop. Blocking - call it
    from a worker thread, never from the event loop."""
    loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(factory())
    finally:
        asyncio.set_event_loop(None)
        loop.close()


class _ProactorLoopThread:
    """One ProactorEventLoop, on one background thread, alive for the process
    - every CLI spawn on Windows runs on it instead of getting its own.

    Building a fresh OS thread and a fresh ProactorEventLoop (with the IOCP
    handle underneath it) per model call, and tearing both down straight
    after, is pure per-call overhead on the hot path: a knowledge compilation
    does that 4-6 times in a row and a campaign many more.

    Shared by every provider, so a mixed run - some roles on Claude, some on
    Codex - still costs exactly one loop.
    """

    _instance: "_ProactorLoopThread | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self.loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._run_forever, name="ai-cli-proactor", daemon=True
        )
        self._thread.start()

    def _run_forever(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    @classmethod
    def instance(cls) -> "_ProactorLoopThread":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def run[T](self, factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """Schedule one coroutine on the persistent loop and await it from the
        caller's own loop - `run_coroutine_threadsafe` is the standard bridge
        for exactly this, and `wrap_future` hands its result back as something
        the caller's loop can `await` directly."""
        future = asyncio.run_coroutine_threadsafe(factory(), self.loop)
        return await asyncio.wrap_future(future)

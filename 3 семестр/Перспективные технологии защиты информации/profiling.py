"""Лёгкая профилировка этапов пайплайна.

Включается через env PROFILING=1. При выключенном — measure() просто
ничего не делает, никаких накладных расходов кроме вызова contextmanager.
"""

import os
import time
import threading
from contextlib import contextmanager


class Stats:
    def __init__(self):
        self._lock  = threading.Lock()
        self._data  = {}

    def add(self, name: str, dt: float):
        with self._lock:
            self._data.setdefault(name, []).append(dt)

    def dump(self, title: str = ""):
        with self._lock:
            items = sorted(self._data.items())
        if not items:
            return
        print(f"\n=== Stats {title} ===")
        print(f"{'phase':<32s} {'n':>6s} {'avg, ms':>10s} "
              f"{'min, ms':>10s} {'max, ms':>10s} {'total, ms':>11s}")
        for name, times in items:
            n     = len(times)
            total = sum(times) * 1000
            print(f"{name:<32s} {n:>6d} {total/n:>10.3f} "
                  f"{min(times)*1000:>10.3f} {max(times)*1000:>10.3f} "
                  f"{total:>11.3f}")

    def reset(self):
        with self._lock:
            self._data.clear()


PROFILING = bool(os.environ.get("PROFILING"))
STATS = Stats()

@contextmanager
def measure(name: str, enabled: bool = None):
    if enabled is None:
        enabled = PROFILING
    if not enabled:
        yield
        return
    t = time.perf_counter()
    try:
        yield
    finally:
        STATS.add(name, time.perf_counter() - t)

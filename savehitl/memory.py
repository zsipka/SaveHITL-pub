"""Peak memory of this process, converted by platform, and a memory watchdog.

`resource.getrusage(...).ru_maxrss` is reported in bytes on macOS and in kilobytes on Linux. This module converts it to
bytes: factor 1 on macOS ("darwin"), factor 1,024 on Linux. On any other platform the raw value is kept with unit
"unknown", one line is printed, and the run continues. Every record holds the bytes, the raw value and the platform.
"""
import resource
import sys
import threading
import time

WATCHDOG_LIMIT_BYTES = 8.0e9

_FACTORS = {"darwin": (1, "bytes"), "linux": (1024, "kilobytes")}
_warned = []


def platform_factor(platform=None):
    """(factor to bytes, unit of the raw value) for a `sys.platform` value; (None, 'unknown') if not known."""
    p = sys.platform if platform is None else platform
    key = "linux" if p.startswith("linux") else p
    return _FACTORS.get(key, (None, "unknown"))


def convert(raw, platform=None):
    """A peak-memory record from a raw `ru_maxrss` value."""
    p = sys.platform if platform is None else platform
    factor, unit = platform_factor(p)
    if factor is None:
        if not _warned:
            print(f"Peak memory: platform {p!r} not known; raw value kept with unit 'unknown'.")
            _warned.append(p)
        return {"bytes": None, "raw": int(raw), "raw_unit": unit, "platform": p}
    return {"bytes": int(raw) * factor, "raw": int(raw), "raw_unit": unit, "platform": p}


def peak(children=False):
    """Peak resident memory of this process (or of its finished child processes), as a record."""
    who = resource.RUSAGE_CHILDREN if children else resource.RUSAGE_SELF
    return convert(resource.getrusage(who).ru_maxrss)


def peak_bytes():
    """Peak resident memory of this process in bytes, or None on a platform not known."""
    return peak()["bytes"]


class Watchdog:
    """Checks the process's peak memory every `interval` seconds; above `limit` bytes it records the event and, if
    `stop` is set, interrupts the main thread. It never enters a computation."""

    def __init__(self, limit=WATCHDOG_LIMIT_BYTES, interval=1.0, stop=True):
        self.limit, self.interval, self.stop = limit, interval, stop
        self.fired = None
        self.high_water = 0
        self._halt = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        import _thread
        while not self._halt.wait(self.interval):
            b = peak_bytes()
            if b is None:
                continue
            self.high_water = max(self.high_water, b)
            if b > self.limit and self.fired is None:
                self.fired = {"bytes": b, "limit": self.limit, "time": time.strftime("%Y-%m-%d %H:%M:%S %Z")}
                print(f"Memory watchdog: peak {b:,} B above the limit {self.limit:,.0f} B.")
                if self.stop:
                    _thread.interrupt_main()
                return

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._halt.set()
        self._thread.join(timeout=5)
        b = peak_bytes()
        if b is not None:
            self.high_water = max(self.high_water, b)
        return False

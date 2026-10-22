"""Build tests of the platform conversion of peak memory and of the watchdog."""
import time

from savehitl import memory


def test_factor_macos_bytes():
    assert memory.convert(5_830_000_000, "darwin") == {"bytes": 5_830_000_000, "raw": 5_830_000_000,
                                                       "raw_unit": "bytes", "platform": "darwin"}


def test_factor_linux_kilobytes():
    r = memory.convert(5_693_359, "linux")
    assert r["bytes"] == 5_693_359 * 1024 and r["raw"] == 5_693_359 and r["raw_unit"] == "kilobytes"


def test_unknown_platform_keeps_raw(capsys):
    r = memory.convert(123, "win32")
    assert r == {"bytes": None, "raw": 123, "raw_unit": "unknown", "platform": "win32"}


def test_watchdog_limit_unchanged():
    assert memory.WATCHDOG_LIMIT_BYTES == 8.0e9


def test_watchdog_fires_above_limit_on_this_platform():
    with memory.Watchdog(limit=1, interval=0.05, stop=False) as w:     # any process is above 1 byte
        time.sleep(0.3)
    assert w.fired is not None and w.fired["bytes"] > 1


def test_watchdog_quiet_below_limit():
    with memory.Watchdog(limit=1e15, interval=0.05, stop=False) as w:
        time.sleep(0.2)
    assert w.fired is None and w.high_water > 0

"""Shared by the steps: arguments, locations, file checksums, and the assertion log.

Every assertion a step makes is written to the run's own log (`logs/assertions.jsonl`) with its outcome. A failed
assertion stops the step.
"""
import argparse
import hashlib
import json
import os
import sys
import time

from .. import memory
from ..runner import Layout


def args(extra=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout-root", required=True)
    ap.add_argument("--out", required=True)
    for name, kw in (extra or []):
        ap.add_argument(name, **kw)
    a = ap.parse_args()
    a.L = Layout(a.layout_root)
    a.step = os.path.basename(os.path.abspath(a.out))
    return a


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def tree_sha(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            if f == ".DS_Store" or f.startswith("_"):
                continue
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = sha256(p)
    return dict(sorted(out.items()))


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


class Asserts:
    """check(condition, name, **details): records the outcome in logs/assertions.jsonl; stops on failure."""

    def __init__(self, a):
        self.path = os.path.join(a.L.logs, "assertions.jsonl")
        self.step = a.step
        os.makedirs(a.L.logs, exist_ok=True)

    def check(self, ok, name, **details):
        rec = {"t": now(), "step": self.step, "assertion": name, "ok": bool(ok), **details}
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        if not ok:
            raise SystemExit(f"STOP ({self.step}): {name} {json.dumps(details, default=str)[:2000]}")


def input_sha(L, rel):
    """Expected sha256 of a framework or FiFAR file (path relative to the framework clone) from the input checksum list."""
    import csv
    with open(os.path.join(L.results, "input_checksums.csv")) as f:
        for r in csv.DictReader(f):
            if r["path"] == rel:
                return r["sha256"]
    raise KeyError(rel)


def write_record(a, rec):
    """The step's own record (outputs/<step>/record.json): output checksums, versions, memory."""
    import numpy, pandas
    rec = dict(rec, finished=now(), peak_memory=memory.peak(), python=sys.version.split()[0],
               numpy=numpy.__version__, pandas=pandas.__version__)
    with open(os.path.join(a.out, "record.json"), "w") as f:
        json.dump(rec, f, indent=1, default=str)

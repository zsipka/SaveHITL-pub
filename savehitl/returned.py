"""The folder the run hands back after it finishes: a description of the run's own outputs, small enough to download.

It holds no alert-level row. For each output file of each step:
  * a table with no alert-level rows (cell measures, intervals, verdicts, summaries, the router's model list): copied
    as it is;
  * an alert-level file (any parquet, pickle or NumPy file, any table with a `case_id` column, and the router's training
    files): its per-column summary instead, one row per column with count, sum, sum of absolute values, minimum and
    maximum; columns that are not numbers get their count, number of distinct values and the sha256 of their
    values in order.
Also: the table files the notebook names (`tables/`, copied, or summarised if alert-level), each views step's
`manifest.json` (what it showed, and any study text that did not match this run), each step's `record.json` (output checksums, versions, peak memory), the run's own logs (`logs/`), and the
sha256 of each of the 250 refitted router models (`router/router_models.csv`, copied). It describes the run's outputs
and compares nothing.

`build(L)` writes `returned/` and `savehitl_returned_outputs.zip` at the repository root and returns the zip's path.
"""
import csv
import hashlib
import json
import os
import pickle
import shutil
import zipfile

SUMMARY_COLUMNS = ["file", "table", "column", "dtype", "count", "sum", "sum_abs", "min", "max", "n_distinct",
                   "values_sha256"]
ALERT_LEVEL_SUFFIXES = (".parquet", ".pkl", ".npy")
NOT_COPIED = ("_done.json", "_script_console.log")


def _num(x):
    return repr(float(x))


def summarise_frame(df, file, table=""):
    """Per-column summary rows of one table (pandas DataFrame); the index is summarised as a column named after it."""
    import numpy as np
    import pandas as pd
    rows = []
    frame = df.reset_index() if (df.index.name is not None or not isinstance(df.index, pd.RangeIndex)) else df
    for c in frame.columns:
        s = frame[c]
        base = {"file": file, "table": table, "column": str(c), "dtype": str(s.dtype), "count": int(s.notna().sum())}
        if s.dtype.kind in "biuf":
            v = s.to_numpy(dtype=np.float64)
            v = v[~np.isnan(v)]
            base.update({"sum": _num(v.sum()) if v.size else "", "sum_abs": _num(np.abs(v).sum()) if v.size else "",
                         "min": _num(v.min()) if v.size else "", "max": _num(v.max()) if v.size else "",
                         "n_distinct": "", "values_sha256": ""})
        else:
            text = "\n".join("" if x is None else str(x) for x in s.astype(object).tolist())
            base.update({"sum": "", "sum_abs": "", "min": "", "max": "", "n_distinct": int(s.nunique(dropna=True)),
                         "values_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        rows.append(base)
    return rows


def summarise_file(path, rel):
    """Summary rows of one alert-level file."""
    import numpy as np
    import pandas as pd
    if path.endswith(".parquet"):
        return summarise_frame(pd.read_parquet(path), rel)
    if path.endswith(".pkl"):
        with open(path, "rb") as f:
            obj = pickle.load(f)
        rows = []
        for k in obj:
            rows += summarise_frame(obj[k], rel, str(k))
        return rows
    if path.endswith(".npy"):
        a = np.load(path, mmap_mode="r")
        tot = tot_abs = 0.0
        mn, mx = None, None
        for r0 in range(0, a.shape[0], 2000):
            b = np.asarray(a[r0:r0 + 2000], dtype=np.float64)
            tot += float(b.sum()); tot_abs += float(np.abs(b).sum())
            mn = float(b.min()) if mn is None else min(mn, float(b.min()))
            mx = float(b.max()) if mx is None else max(mx, float(b.max()))
        return [{"file": rel, "table": "", "column": "whole array", "dtype": str(a.dtype), "count": int(a.size),
                 "sum": _num(tot), "sum_abs": _num(tot_abs), "min": _num(mn), "max": _num(mx), "n_distinct": "",
                 "values_sha256": ""}]
    return summarise_frame(pd.read_csv(path, float_precision="round_trip"), rel)


def is_alert_level(path, step):
    if path.endswith(ALERT_LEVEL_SUFFIXES) or step == "train_alert":
        return True
    if path.endswith(".csv"):
        with open(path, newline="") as f:
            header = next(csv.reader(f), [])
        return "case_id" in header
    return False


def build(L, name="savehitl_returned_outputs"):
    dest = os.path.join(L.root, "returned")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    summary_rows, copied = [], []
    for step in sorted(os.listdir(L.outputs)):
        sdir = os.path.join(L.outputs, step)
        if not os.path.isdir(sdir):
            continue
        for d, _, fs in os.walk(sdir):
            for fn in sorted(fs):
                p = os.path.join(d, fn)
                rel = os.path.relpath(p, L.outputs)
                if fn in NOT_COPIED or fn.startswith("."):
                    continue
                if fn in ("record.json", "teams.json", "manifest.json") or fn.endswith((".yaml", ".yml")):
                    if not fn.endswith((".yaml", ".yml")) or step != "generator":
                        os.makedirs(os.path.dirname(os.path.join(dest, rel)), exist_ok=True)
                        shutil.copy(p, os.path.join(dest, rel)); copied.append(rel)
                    continue
                if is_alert_level(p, step):
                    summary_rows += summarise_file(p, rel)
                elif fn.endswith(".csv"):
                    os.makedirs(os.path.dirname(os.path.join(dest, rel)), exist_ok=True)
                    shutil.copy(p, os.path.join(dest, rel)); copied.append(rel)
    tdir = os.path.join(L.root, "tables")                # the table files the notebook names (aggregates)
    if os.path.isdir(tdir):
        for fn in sorted(os.listdir(tdir)):
            p = os.path.join(tdir, fn)
            rel = os.path.join("tables", fn)
            if not fn.endswith(".csv"):
                continue
            if is_alert_level(p, "tables"):
                summary_rows += summarise_file(p, rel)
            else:
                os.makedirs(os.path.join(dest, "tables"), exist_ok=True)
                shutil.copy(p, os.path.join(dest, rel)); copied.append(rel)
    with open(os.path.join(dest, "per_column_summaries.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        w.writeheader()
        w.writerows(summary_rows)
    if os.path.isdir(L.logs):
        shutil.copytree(L.logs, os.path.join(dest, "logs"))
    with open(os.path.join(dest, "manifest.json"), "w") as f:
        json.dump({"copied": copied, "summarised_files": sorted({r["file"] for r in summary_rows}),
                   "summary_rows": len(summary_rows)}, f, indent=1)
    zpath = os.path.join(L.root, name + ".zip")
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(dest):
            for fn in fs:
                p = os.path.join(d, fn)
                z.write(p, os.path.join("returned", os.path.relpath(p, dest)))
    return zpath


if __name__ == "__main__":       # run by the notebook's last cell in the pinned environment: python -m savehitl.returned <root>
    import sys
    from .runner import Layout
    print(build(Layout(sys.argv[1])))

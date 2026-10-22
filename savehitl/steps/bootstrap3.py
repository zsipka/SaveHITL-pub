"""Step: policy 3's bootstrap, on the per-resample counts saved by policy 2's bootstrap (no index matrix is drawn here,
and there is no fallback to a fresh draw).

  1. Checks on the counts, in order, before any comparison: T-a (file sha256; after loading, array-bytes sha256, shape
     and dtype equal policy 2's record), T-b (sha256 of policy 3's own ascending case_id vector equals the record's),
     T-c (every row sums to 4,457, 64-bit), T-d (a fresh RandomState(2026).randint(0, 4457, size=(1000, 4457)), as
     counts, equals rows 0 to 999), NumPy version equal to policy 2's run. Each with a negative control on a copy.
  2. The intervals, as policy 2's, with policy 3's comparisons (against policy 2 too) and 66 deciding results.
  3. Build tests: the point estimates equal the seed means of the replay's cell measures (within 1e-9), also the points
     against policy 2 on expected loss and accepted frauds; the parts of each difference add up (within 1e-9).
The computation is the study's bootstrap code (`savehitl.boot`), unchanged; memory watchdog as policy 2's.

Output: p3_boot_intervals.csv.
"""
import json
import os
import time

import numpy as np
import pandas as pd

from .. import memory
from ..boot import boot_core as BC
from ..boot import engine
from ..boot import measures as M
from . import _chain as CH
from . import _common as C

LAMBDAS = (0.035, 0.0537, 0.057, 0.171)
N_DECIDING = 66
N, B, SEED, G1_ROWS = 4457, 50000, 2026, 1000


def main():
    T0 = time.time()
    a = C.args([("--policy1", {"required": True}), ("--policy3", {"required": True}),
                ("--counts-record", {"required": True, "help": "record of the policy 2 bootstrap that saved the counts"}),
                ("--counts-file", {"required": True}), ("--block-rows", {"type": int, "default": 2000})])
    A = C.Asserts(a)
    log = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)  # noqa: E731
    p2m = json.load(open(a.counts_record))
    A.check(bool(p2m.get("build_tests", {}).get("pass")), "policy 2's bootstrap passed its build tests (its counts are reused)")
    case_id, label, age50, p1 = CH.load_p1_arrays(A, a.policy1)
    blocks, Ks = CH.load_blocks(A, CH.step_output(A, a.policy3, "p3_seed_avg_per_case.parquet"), M.P3_COLS, case_id)
    caps = CH.capacities_from_K(Ks)
    cells_path = CH.step_output(A, a.policy3, "p3_cell_measures.csv")
    cm = CH.cell_means(cells_path)
    log(f"inputs loaded; peak {BC.peak_rss()} B")

    with memory.Watchdog(stop=True) as wd:
        t_m = time.time()
        frec = dict(p2m["counts_file"])
        res, counts = BC.m6_checks(a.counts_file, frec, case_id, SEED, N, B, G1_ROWS,
                                   numpy_version_recorded=p2m["bootstrap"]["numpy_version"])
        t_m6 = time.time() - t_m
        for k in ("T-a", "T-b", "T-c", "T-d", "numpy_version"):
            if k in res:
                A.check(res[k]["result"] == "pass", f"{k}: counts check", **{x: y for x, y in res[k].items() if x != "result"})
        A.check(counts is not None, "counts loaded")
        nc = {}
        c1 = counts.copy(); c1[B // 2, N // 2] ^= 1
        nc["T-a"] = BC.sha256_array(c1) != frec["array_bytes_sha256"]
        del c1
        nc["T-b"] = BC.case_order_sha(np.r_[case_id[:-1], case_id[-1] + 1]) != frec["case_order_sha256"]
        c2 = counts[:5].copy(); j = int(np.flatnonzero(c2[0])[0]); c2[0, j] -= 1
        nc["T-c"] = not BC.row_sums_ok(c2, N)[0]
        alt = BC.counts_of_rows(np.random.RandomState(SEED + 1).randint(0, N, size=(min(G1_ROWS, 50), N)), N)
        nc["T-d"] = not np.array_equal(alt, counts[:alt.shape[0]].astype(np.int64))
        del c2, alt
        A.check(all(nc.values()), "negative controls of T-a to T-d caught", **nc)
        log(f"counts checks passed ({t_m6:.1f} s)")
        t_e = time.time()
        rows, erec = engine.run(counts, case_id, label, age50, p1, blocks, caps, 3, LAMBDAS, N_DECIDING, "this run",
                                a.block_rows, log)
        t_engine = time.time() - t_e
    A.check(wd.fired is None, "memory watchdog did not fire", limit=wd.limit, high_water=wd.high_water)
    df = pd.DataFrame(rows)
    n_dec = df[(df.level == "adjusted") & (df.version == engine.MEAN)].shape[0]
    A.check(n_dec == N_DECIDING, "66 deciding results at the adjusted level", n_deciding=n_dec)

    bt = 0.0
    lv = df[(df.comparison == "level") & (df.level == "95%") & (df.version != engine.MEAN)]
    for (t, v, lab, lam), g in cm.groupby(["team", "version", "capacity_label", "lambda"]):
        q = lv[(lv.team == t) & (lv.version == v) & (lv.capacity_label == lab)]
        pairs = [(q[(q.measure == "expected_loss_total") & (q["lambda"] == lam)], g["expected_loss_total"]),
                 (q[q.measure == "regulatory_exposure_accepted_frauds_count"], g["regulatory_exposure_accepted_frauds_count"]),
                 (q[q.measure == "fairness_exposure_age_gap_signed"], g["fairness_exposure_age_gap_signed"]),
                 (q[q.measure == "false_rejections_50_plus_count"], g["false_rejections_50_plus"])]
        for x, y in pairs:
            if len(x) != 1:
                A.check(False, "one point estimate per cell", team=t, version=int(v), capacity=lab, lam=lam)
            bt = max(bt, abs(float(x["point_estimate"].iloc[0]) - float(y.iloc[0])))
    cm2 = pd.read_csv(cells_path, float_precision="round_trip", dtype={"capacity_label": str}).groupby(
        ["team", "version", "capacity_label", "lambda"])[["difference_expected_loss_vs_policy_2",
                                                          "difference_accepted_frauds_vs_policy_2"]].mean().reset_index()
    lv2 = df[(df.comparison == "vs_policy_2") & (df.level == "95%") & (df.version != engine.MEAN)]
    bt2, n_bt2 = 0.0, 0
    for (t, v, lab, lam), g in cm2.groupby(["team", "version", "capacity_label", "lambda"]):
        q = lv2[(lv2.team == t) & (lv2.version == v) & (lv2.capacity_label == lab)]
        for x, y in ((q[(q.measure == "difference_expected_loss") & (q["lambda"] == lam)], g["difference_expected_loss_vs_policy_2"]),
                     (q[q.measure == "difference_accepted_frauds"], g["difference_accepted_frauds_vs_policy_2"])):
            if len(x) != 1:
                A.check(False, "one point estimate per cell against policy 2", team=t, version=int(v), capacity=lab, lam=lam)
            bt2 = max(bt2, abs(float(x["point_estimate"].iloc[0]) - float(y.iloc[0]))); n_bt2 += 1
    build = {"point_vs_replay_cell_means_max_abs": bt, "point_vs_replay_ok": bt <= 1e-9,
             "vs_policy_2_point_vs_replay_cell_means_max_abs": bt2, "vs_policy_2_points_compared": n_bt2,
             "vs_policy_2_point_vs_replay_ok": bt2 <= 1e-9,
             "parts_add_up_max_abs": erec["max_abs_parts_minus_difference"],
             "parts_add_up_ok": erec["max_abs_parts_minus_difference"] <= 1e-9}
    build["pass"] = bool(build["point_vs_replay_ok"] and build["vs_policy_2_point_vs_replay_ok"] and build["parts_add_up_ok"])
    iname = "p3_boot_intervals.csv"
    df.to_csv(os.path.join(a.out, iname), index=False, float_format="%.17g")
    C.write_record(a, {"step": a.step, "build_tests": build, "counts_checks": res,
                       "counts_negative_controls": nc, "counts_record": {k: frec.get(k) for k in (
                           "file_sha256", "array_bytes_sha256", "case_order_sha256", "shape", "dtype")},
                       "bootstrap": {"B": B, "percentile_method": "linear (NumPy default)",
                                     "deciding_level": {"n_deciding": N_DECIDING,
                                                        "percentiles": list(BC.adjusted_percentiles(N_DECIDING))},
                                     "zero_threshold": BC.ZERO, "g3_dropped_resamples": erec["g3_dropped"], "g3_limit": 500},
                       "engine": erec, "watchdog": {"limit": wd.limit, "high_water": wd.high_water, "fired": wd.fired},
                       "runtime_s": {"counts_checks": round(t_m6, 3), "intervals": round(t_engine, 3),
                                     "in_process_total": round(time.time() - T0, 3)},
                       "outputs_sha256": {iname: C.sha256(os.path.join(a.out, iname))}})
    A.check(build["pass"], "build tests of the bootstrap", **build)


if __name__ == "__main__":
    main()

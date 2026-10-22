"""Step: policy 2's bootstrap (B = 50,000 case resamples), the intervals of every measure and comparison.

  1. The index matrix, in one call: numpy.random.RandomState(2026).randint(0, 4457, size=(50000, 4457)), int64. G1: its
     rows 0 to 999 equal a fresh 1,000-row draw, and their sha256 equals the one the policy 1 intervals step recorded.
  2. Counts per resample, row block by row block, with G-a (every count at most 255, before the cast) and G-b (each row
     sums to 4,457 in 64 bits); stored as uint8; the index matrix is then freed.
  3. The counts are saved (NumPy .npy) for policy 3's bootstrap, read back and compared (sha256 of the array bytes).
  4. The intervals, from the same counts: per capacity, the per-case seed sums of the 15 team instances are summed over
     each resample exactly (integer-valued float64), the measures formed, 95% percentile intervals (NumPy's linear
     method) and, for the 61 deciding results, the adjusted level 2.5/61 % and 100 - 2.5/61 %.
  5. Build tests: the point estimates equal the seed means of the replay's cell measures (within 1e-9); the two parts of
     each difference add up to it (within 1e-9); the section 9 contrasts fixed by construction are at most 0.
The computation is the study's bootstrap code (`savehitl.boot`), unchanged. A memory watchdog (8.0e9 B, peak memory
converted by platform) interrupts the step above its limit.

Outputs: p2_boot_intervals.csv, p2_bootstrap_counts_uint8.npy (input of policy 3's bootstrap; not a result table).
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
N_DECIDING = 61
N, B, SEED, G1_ROWS = 4457, 50000, 2026, 1000


def main():
    T0 = time.time()
    a = C.args([("--policy1", {"required": True}), ("--policy1-intervals", {"required": True}),
                ("--policy2", {"required": True}), ("--block-rows", {"type": int, "default": 2000})])
    A = C.Asserts(a)
    log = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)  # noqa: E731
    case_id, label, age50, p1 = CH.load_p1_arrays(A, a.policy1)
    blocks, Ks = CH.load_blocks(A, CH.step_output(A, a.policy2, "p2_seed_avg_per_case.parquet"), M.BASE_COLS, case_id)
    caps = CH.capacities_from_K(Ks)
    cm = CH.cell_means(CH.step_output(A, a.policy2, "p2_cell_measures.csv"))
    p1_rows_sha = json.load(open(os.path.join(a.policy1_intervals, "record.json")))["bootstrap"]["index_rows_sha256_int64_bytes"]
    log(f"inputs loaded; peak {BC.peak_rss()} B")

    with memory.Watchdog(stop=True) as wd:
        t_b = time.time()
        idx = BC.draw_index(SEED, N, B)
        t_draw = time.time() - t_b
        idx_sha = BC.sha256_array(idx)
        rows_sha = BC.sha256_array(idx[:G1_ROWS])
        g1_ok, g1_ndiff = BC.check_g1(idx, SEED, N, G1_ROWS)
        A.check(g1_ok and rows_sha == p1_rows_sha, "G1: rows 0 to 999 equal a fresh 1,000-row draw and policy 1's index rows",
                cells_differing=g1_ndiff, rows_sha256=rows_sha, policy_1_rows_sha256=p1_rows_sha)
        try:
            counts, crec = BC.counts_from_index(idx, N, a.block_rows)
        except BC.GuardError as e:
            A.check(False, f"{e.guard}: counts guard", message=str(e))
        A.check(crec["G-a"] == "pass", "G-a: every count at most 255, before the cast", max_count=crec["G-a_max_count"])
        A.check(crec["G-b"] == "pass", "G-b: every row sums to 4,457 (64-bit)", rows_not_summing=crec["G-b_rows_not_summing"])
        blk = idx[:max(a.block_rows, G1_ROWS)].copy()
        del idx                                                      # freed after its checksum and G1
        b2 = blk[:a.block_rows].copy(); b2[0, :256] = 0               # negative control: one case drawn 256 times
        try:
            BC.counts_from_index(b2, N, a.block_rows); nc_ga = False
        except BC.GuardError as e:
            nc_ga = e.guard == "G-a"
        c2 = counts[:a.block_rows].copy(); j = int(np.flatnonzero(c2[0])[0]); c2[0, j] -= 1
        nc_gb = not BC.row_sums_ok(c2, N)[0]
        alt = blk[:G1_ROWS].copy(); alt[0, 0] = (alt[0, 0] + 1) % N
        nc_g1 = (not np.array_equal(alt, np.random.RandomState(SEED).randint(0, N, size=(G1_ROWS, N)))) and \
            BC.sha256_array(alt) != p1_rows_sha
        del b2, c2, alt, blk
        A.check(nc_ga and nc_gb and nc_g1, "negative controls of G-a, G-b and G1 caught", G_a=nc_ga, G_b=nc_gb, G1=nc_g1)
        t_counts = time.time() - t_b
        log(f"counts built; index freed; peak {BC.peak_rss()} B")

        cname = "p2_bootstrap_counts_uint8.npy"
        cpath = os.path.join(a.out, cname)
        frec = BC.save_counts(counts, cpath)
        frec["path"] = cname
        frec["case_order_sha256"] = BC.case_order_sha(case_id)
        frec["case_order_encoding"] = "ascending case_id as little-endian int64 bytes"
        A.check(frec["read_back_array_bytes_sha256_equal"], "counts file read back equal (sha256 of the array bytes)")

        t_e = time.time()
        rows, erec = engine.run(counts, case_id, label, age50, p1, blocks, caps, 2, LAMBDAS, N_DECIDING, "this run",
                                a.block_rows, log)
        t_engine = time.time() - t_e
    A.check(wd.fired is None, "memory watchdog did not fire", limit=wd.limit, high_water=wd.high_water)
    df = pd.DataFrame(rows)
    n_dec = df[(df.level == "adjusted") & (df.version == engine.MEAN) & (df.deciding_kind == "decides")].shape[0]
    A.check(n_dec == N_DECIDING and df[df.level == "adjusted"].shape[0] == (N_DECIDING + 2) * 6,
            "61 deciding results (and P2-K's two by construction) at the adjusted level", n_deciding=n_dec)

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
    build = {"point_vs_replay_cell_means_max_abs": bt, "point_vs_replay_ok": bt <= 1e-9,
             "parts_add_up_max_abs": erec["max_abs_parts_minus_difference"],
             "parts_add_up_ok": erec["max_abs_parts_minus_difference"] <= 1e-9,
             "bias_x_capacity_I_le_0_ok": all(x <= 1e-9 for x in erec["bias_x_capacity_max_I_by_construction"].values())}
    build["pass"] = bool(build["point_vs_replay_ok"] and build["parts_add_up_ok"] and build["bias_x_capacity_I_le_0_ok"])
    iname = "p2_boot_intervals.csv"
    df.to_csv(os.path.join(a.out, iname), index=False, float_format="%.17g")
    C.write_record(a, {"step": a.step, "build_tests": build, "counts": crec, "counts_file": frec,
                       "bootstrap": {"generator": BC.GENERATOR, "call": BC.EXACT_CALL, "B": B, "seed": SEED, "dtype": "int64",
                                     "numpy_version": np.__version__, "index_sha256_int64_c_order": idx_sha,
                                     "rows_0_999_sha256": rows_sha, "G1": "pass" if g1_ok else "fail",
                                     "percentile_method": "linear (NumPy default)",
                                     "deciding_level": {"n_deciding": N_DECIDING,
                                                        "percentiles": list(BC.adjusted_percentiles(N_DECIDING))},
                                     "zero_threshold": BC.ZERO, "g3_dropped_resamples": erec["g3_dropped"], "g3_limit": 500},
                       "engine": erec, "watchdog": {"limit": wd.limit, "high_water": wd.high_water, "fired": wd.fired},
                       "runtime_s": {"draw": round(t_draw, 3), "index_to_counts": round(t_counts, 3),
                                     "intervals": round(t_engine, 3), "in_process_total": round(time.time() - T0, 3)},
                       "outputs_sha256": {iname: C.sha256(os.path.join(a.out, iname)), cname: frec["file_sha256"]}})
    A.check(build["pass"], "build tests of the bootstrap", **build)


if __name__ == "__main__":
    main()

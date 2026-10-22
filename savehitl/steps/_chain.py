"""Readers of the chain's own outputs, shared by the steps after policy 1, and the constants of the replays.

Every reader checks what the study's scripts checked when they read the same file from the study's records (row counts,
case order, ranges); here the file is the output of an earlier step of this run, so its checksum is taken from that
step's own record (`record.json`) rather than from a register.
"""
import json
import os
import re
from fractions import Fraction

import numpy as np
import pandas as pd

from . import _common as C

N = 4457
TEST_MONTH = 7
SEEDS = (1, 2, 3, 4, 5)                       # review order and dealing
DRAW_SEED_OFFSET = 100                        # deference draws: RandomState(100 + seed)
DEFER_P = 0.8                                 # team B: strictly below 0.8
VERSIONS = (1, 2, 3, 4, 5)
TEAMS = ("A", "B", "C")
LAMBDAS = (0.035, 0.0537, 0.057, 0.171)
ANCHOR = 0.057
REALISTIC = ("0.65", "0.70", "0.75", "0.80", "0.85", "0.90", "10/11", "0.95", "1.00")

CALL_ORDER = "order = numpy.random.RandomState(seed).permutation(4457)"
CALL_SLOT = ("slot = numpy.argsort(rs.rand(446, 10), axis=1, kind='stable').ravel()[:4457]  "
             "(same RandomState object, after the permutation)")
CALL_DRAW = "deference_draw = numpy.random.RandomState(100 + seed).rand(4457)"


def step_output(A, step_dir, name):
    """Path of an output of an earlier step, checked against the sha256 that step recorded."""
    rec = json.load(open(os.path.join(step_dir, "record.json")))
    p = os.path.join(step_dir, name)
    want = rec.get("outputs_sha256", {}).get(name)
    A.check(want is not None and C.sha256(p) == want, "input equal to the checksum its step recorded",
            file=os.path.relpath(p, os.path.dirname(step_dir)))
    return p


def capacities():
    """22 capacities: 0, 0.05, ..., 1 and 10/11, ascending; K = floor(capacity x 4,457) exactly."""
    caps = sorted([Fraction(k, 20) for k in range(21)] + [Fraction(10, 11)])
    out = []
    for c in caps:
        K = (c.numerator * N) // c.denominator
        label = "10/11" if c == Fraction(10, 11) else f"{float(c):.2f}"
        out.append({"label": label, "frac": c, "value": float(c), "K": int(K)})
    assert len(out) == 22 and [o["K"] for o in out if o["label"] == "10/11"] == [4051]
    assert [o["K"] for o in out if o["label"] == "0.75"] == [3342]
    return out


def load_p1(A, policy1_dir):
    """Policy 1's per-case file, ascending case_id (read exactly: round-trip parsing)."""
    p = step_output(A, policy1_dir, "p1_per_case.csv")
    p1 = pd.read_csv(p, float_precision="round_trip")
    A.check(p1["case_id"].is_unique and len(p1) == N and bool((p1["month"] == TEST_MONTH).all()),
            "policy 1 per-case file: 4,457 unique alerts of the test month")
    return p1.sort_values("case_id").reset_index(drop=True)


def twin_number(name):
    m = re.fullmatch(r"unbiased#(\d+)", name)
    assert m, name
    return int(m.group(1))


def load_teams(A, draw_dir):
    """Version r = drawn team r: its list `twins_in_slot_order` (slot j = the member with the j-th smallest number)."""
    p = os.path.join(draw_dir, "teams.json")
    rec = json.load(open(p))
    A.check(C.sha256(p) == json.load(open(os.path.join(draw_dir, "record.json")))["teams_json_sha256"],
            "teams.json equal to the checksum the draw step recorded")
    A.check(set(rec["teams"]) == {str(k) for k in VERSIONS}, "five drawn teams")
    teams = {}
    for k in VERSIONS:
        members = list(rec["teams"][str(k)]["twins_in_slot_order"])
        nums = [twin_number(m) for m in members]
        A.check(len(nums) == 10 and len(set(nums)) == 10 and nums == sorted(nums),
                "drawn team: 10 different reviewers in ascending number order", team=k)
        teams[k] = members
    return teams


def reference_lists(A, draw_dir):
    """The draw's lists in slot order, derived a second way inside the draw file: the draw-order numbers sorted as
    numbers (as the study's P2-M (5) reference)."""
    rec = json.load(open(os.path.join(draw_dir, "teams.json")))
    out = {}
    for r in VERSIONS:
        t = rec["teams"][str(r)]
        derived = [f"unbiased#{i}" for i in sorted(int(x) for x in t["numbers_in_draw_order"])]
        A.check(list(t["twins_in_slot_order"]) == derived, "slot order equal to the draw order sorted as numbers", team=r)
        out[r] = derived
    return out


def slots_equal_list(slot, expert, want):
    """P2-M (5) for one replay: every slot 0..9 used, one reviewer per slot, the reviewer in slot j is want[j]."""
    pairs = {}
    for s, e in zip(slot, expert):
        pairs.setdefault(int(s), set()).add(str(e))
    got = [sorted(pairs[j])[0] if j in pairs and len(pairs[j]) == 1 else None for j in range(10)]
    return bool(set(pairs) == set(range(10)) and all(len(v) == 1 for v in pairs.values()) and got == list(want))


def case_ids_of_months(L, months):
    alerts = pd.read_parquet(os.path.join(L.fifar, "alert_data", "processed_data", "alerts.parquet"), columns=["month"])
    return alerts.index[alerts["month"].isin(list(months))]


def load_twins(A, L, generator_dir, months):
    """The regenerated reviewers' decisions on the given file months (the generator step's file, checksum from its
    record); rows of other months dropped at once; index exactly the alerts of those months."""
    p = os.path.join(generator_dir, "data", "expert_predictions.parquet")
    rec = json.load(open(os.path.join(generator_dir, "record.json")))
    A.check(C.sha256(p) == rec["outputs_sha256"]["expert_predictions.parquet"],
            "reviewers' decisions equal to the checksum the generator step recorded")
    keep = case_ids_of_months(L, months)
    df = pd.read_parquet(p)
    df = df.loc[df.index.isin(keep)]
    A.check(df.index.name == "case_id" and df.index.is_unique and len(df) == len(keep) and bool(df.index.isin(keep).all()),
            "reviewers' decisions: exactly the alerts of the months", months=list(months))
    return df


def draw_allocation(seed):
    rs = np.random.RandomState(seed)
    order = rs.permutation(N)
    slot = np.argsort(rs.rand(446, 10), axis=1, kind="stable").ravel()[:N]
    return order, slot


def draw_deference(seed):
    return np.random.RandomState(DRAW_SEED_OFFSET + seed).rand(N)


def setup_name(r, s):
    return f"shuffle_{s}#drawn_{r}"


# --- bootstrap inputs (as the study's bootstrap input reader, on this run's own files) ------------------------------

def load_p1_arrays(A, policy1_dir):
    p1 = pd.read_csv(step_output(A, policy1_dir, "p1_per_case.csv"), float_precision="round_trip")
    A.check(len(p1) == N and p1["case_id"].is_unique and p1["case_id"].is_monotonic_increasing,
            "policy 1 per-case file: 4,457 alerts in ascending case_id")
    return (p1["case_id"].to_numpy().astype(np.int64), p1["label_fraud"].to_numpy().astype(np.int64),
            p1["age_50_plus"].to_numpy().astype(np.int64), p1["p1_reject"].to_numpy().astype(np.int64))


def load_blocks(A, path, cols, case_ids):
    """Seed-sum blocks of a replay: {(team, version, capacity_label): {column: int64 array}}, each in ascending case_id
    order and equal to policy 1's case order."""
    df = pd.read_parquet(path, columns=["team", "version", "capacity_label", "K", "case_id"] + list(cols))
    A.check(len(df) == 330 * N, "seed sums: 330 blocks of 4,457 alerts", rows=len(df))
    blocks, Ks = {}, {}
    for (t, v, lab), g in df.groupby(["team", "version", "capacity_label"], sort=False, observed=True):
        g = g.sort_values("case_id")
        if not np.array_equal(g["case_id"].to_numpy(), case_ids):
            A.check(False, "seed-sum block in policy 1's case order", team=t, version=int(v), capacity=lab)
        blocks[(str(t), int(v), str(lab))] = {c: g[c].to_numpy().astype(np.int64) for c in cols}
        Ks[str(lab)] = int(g["K"].iloc[0])
    del df
    A.check(len(blocks) == 330, "330 seed-sum blocks")
    return blocks, Ks


def capacities_from_K(Ks):
    """The 22 capacities, ascending; labels and K as in the replay's seed sums."""
    vals = {lab: (10 / 11 if lab == "10/11" else float(lab)) for lab in Ks}
    caps = [{"label": lab, "K": Ks[lab], "value": vals[lab]} for lab in sorted(Ks, key=lambda q: vals[q])]
    assert len(caps) == 22 and [c["K"] for c in caps if c["label"] == "10/11"] == [4051]
    assert [c["K"] for c in caps if c["label"] == "0.75"] == [3342]
    for c in caps:
        if c["label"] != "10/11":
            assert c["K"] == (int(round(c["value"] * 20)) * N) // 20
    return caps


def cell_means(path):
    """Seed means of a replay's cell measures, per team, version, capacity and cost ratio (build tests only)."""
    cl = pd.read_csv(path, float_precision="round_trip", dtype={"capacity_label": str})
    keep = ["expected_loss_total", "regulatory_exposure_accepted_frauds_count", "fairness_exposure_age_gap_signed",
            "false_rejections_50_plus"]
    return cl.groupby(["team", "version", "capacity_label", "lambda"])[keep].mean().reset_index()

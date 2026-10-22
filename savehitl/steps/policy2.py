"""Step: policy 2 (naive review), the replay, its costing and its tables, on the five drawn teams.

Inputs: policy 1's per-case file; the regenerated reviewers' decisions on the test month (generator step); the drawn
teams (draw step). Per seed 1 to 5: the review order and dealing, and the deference draws, by the exact calls
(`_chain.CALL_ORDER`, `CALL_SLOT`, `CALL_DRAW`). P2-M (5) is asserted before any figure: in every replay the reviewers
in the slots of version r equal list r of the draw in slot order. Per seed, team (A, B, C) and version (1 to 5): each
alert's reviewer, the reviewer's decision, and the decision the team's rule gives if the alert is reviewed. Per capacity
(22): reviewed if the review position is below K, otherwise confirmed without review. Costs at the four cost ratios and
the measures per cell (6,600 cells). The computation is the study's replay script's, unchanged.

Decisions: 1 = alert confirmed (application rejected); 0 = alert dismissed (application accepted).
Outputs: p2_allocation.csv, p2_cell_measures.csv, p2_team_cases.parquet, p2_seed_avg_per_case.parquet.
"""
import hashlib
import os

import numpy as np
import pandas as pd

from . import _chain as CH
from . import _common as C

N = CH.N


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    a = C.args([("--policy1", {"required": True}), ("--generator", {"required": True}), ("--draw", {"required": True})])
    A = C.Asserts(a)
    p1 = CH.load_p1(A, a.policy1)
    case_id = p1["case_id"].to_numpy()
    y = p1["label_fraud"].to_numpy().astype(np.int64)
    old = p1["age_50_plus"].to_numpy().astype(np.int64)
    p1r = p1["p1_reject"].to_numpy().astype(np.int64)
    twins = CH.load_twins(A, a.L, a.generator, (CH.TEST_MONTH,)).sort_index()
    A.check(np.array_equal(twins.index.to_numpy(), case_id) and bool(twins.notna().all().all()),
            "reviewers' alerts equal policy 1's, no missing decision")
    twin_cols = list(twins.columns)
    T = twins.to_numpy().astype(np.int64)                  # N x 50, column j = twin_cols[j]
    A.check(set(np.unique(T)) <= {0, 1}, "decisions only 0 or 1")
    col_of = {name: j for j, name in enumerate(twin_cols)}
    teams = CH.load_teams(A, a.draw)
    caps = CH.capacities()
    leg = y == 0
    fraud = y == 1
    n_leg_old = int((leg & (old == 1)).sum())
    n_leg_yng = int((leg & (old == 0)).sum())
    n_fraud = int(fraud.sum())
    p1_fp = int(((p1r == 1) & leg).sum())
    p1_fn = int(((p1r == 0) & fraud).sum())

    def tree(team, twin, p1dec, age50, draw):
        """Decision on a reviewed case (section 2.1). 1 = alert confirmed (application rejected)."""
        if team == "A":
            return twin.copy()
        if team == "B":
            agree = twin == p1dec
            return np.where(agree, twin, np.where(draw < CH.DEFER_P, p1dec, twin))
        if team == "C":
            return np.where((age50 == 1) & (twin == 0) & (p1dec == 1), 1, twin)
        raise ValueError(team)


    # ------------------------------------------------------------------ allocation and draws per seed
    alloc_rows, seed_info, rank_of, slot_of, draws = [], {}, {}, {}, {}
    for s in CH.SEEDS:
        order, slot = CH.draw_allocation(s)
        order2, slot2 = CH.draw_allocation(s)
        d = CH.draw_deference(s)
        # build test (E-34 1.1): order and dealing byte-identical whether or not the draws are generated
        A.check(order.tobytes() == order2.tobytes() and slot.tobytes() == slot2.tobytes(), "order and dealing byte-identical when drawn twice", seed=s)
        rank = np.empty(N, dtype=np.int64)
        rank[order] = np.arange(N)                    # review position of case i (case order: ascending case_id)
        sc = slot[rank]                               # slot of case i
        rank_of[s], slot_of[s], draws[s] = rank, sc, d
        seed_info[s] = {"draw_sha256_float64": sha256_bytes(d.astype("<f8").tobytes()),
                        "share_draws_below_0.8": float((d < CH.DEFER_P).mean()),
                        "order_sha256_int64": sha256_bytes(order.astype("<i8").tobytes()),
                        "slot_sha256_int64": sha256_bytes(slot.astype("<i8").tobytes())}
        alloc_rows.append(pd.DataFrame({"seed": s, "case_id": case_id, "review_rank": rank, "slot": sc,
                                        "deference_draw": d}))
    p2_allocation = pd.concat(alloc_rows, ignore_index=True)

    # ------------------------------------------------------------------ P2-M (5), before any figure
    LISTS = CH.reference_lists(A, a.draw)
    p2m5_expert, p2m5 = {}, {"replays_tested": 0, "replays_failed": []}
    for s in CH.SEEDS:
        for team in CH.TEAMS:
            for v in CH.VERSIONS:
                e_sv = np.array(teams[v], dtype=object)[slot_of[s]]
                ok = CH.slots_equal_list(slot_of[s], e_sv, LISTS[v])
                p2m5["replays_tested"] += 1
                if not ok:
                    p2m5["replays_failed"].append({"seed": s, "team": team, "version": v})
                p2m5_expert[(s, team, v)] = e_sv
    A.check(not p2m5["replays_failed"] and p2m5["replays_tested"] == len(CH.SEEDS) * len(CH.TEAMS) * len(CH.VERSIONS),
            "P2-M (5): in every replay the reviewers in the slots of version r equal list r in slot order, before any figure",
            **p2m5)

    # ------------------------------------------------------------------ replay
    master_rows = []
    cell_rows = []
    # seed sums per (team, version, capacity index) for the bootstrap input
    acc = {}
    build_tests = {"B_equals_A_when_p_0": True, "B_equals_policy_1_on_reviewed_when_p_1": True,
                   "draws_identical_across_versions_and_capacities": True}
    for s in CH.SEEDS:
        rank, sc, d = rank_of[s], slot_of[s], draws[s]
        for team in CH.TEAMS:
            for v in CH.VERSIONS:
                members = teams[v]
                expert = np.array(members, dtype=object)[sc]
                assert np.array_equal(expert, p2m5_expert[(s, team, v)]), "slots differ from those P2-M (5) checked"
                jcol = np.array([col_of[m] for m in members])[sc]
                twin = T[np.arange(N), jcol]
                dec_rev = tree(team, twin, p1r, old, d)
                if team == "B":   # build tests (E-34 1.1)
                    b0 = np.where(twin == p1r, twin, np.where(d < 0.0, p1r, twin))
                    b1 = np.where(twin == p1r, twin, np.where(d < 1.0 + 1e-12, p1r, twin))
                    build_tests["B_equals_A_when_p_0"] &= bool(np.array_equal(b0, twin))
                    build_tests["B_equals_policy_1_on_reviewed_when_p_1"] &= bool(np.array_equal(b1, p1r))
                    build_tests["draws_identical_across_versions_and_capacities"] &= bool(np.array_equal(d, CH.draw_deference(s)))
                master_rows.append(pd.DataFrame({
                    "seed": s, "team": team, "version": v, "case_id": case_id, "review_rank": rank, "slot": sc,
                    "expert_id": expert, "twin_decision": twin, "p1_reject": p1r, "age_50_plus": old,
                    "label_fraud": y, "deference_draw": d, "decision_if_reviewed": dec_rev}))
                disagree = (twin != p1r)
                deferred = disagree & (d < CH.DEFER_P) if team == "B" else np.zeros(N, dtype=bool)
                cell_c = (old == 1) & (twin == 0) & (p1r == 1)          # C's rule changes the twin's decision
                for ci, cap in enumerate(caps):
                    K = cap["K"]
                    rev = rank < K
                    fin = np.where(rev, dec_rev, 1)
                    key = (team, v, ci)
                    if key not in acc:
                        acc[key] = {"n_seeds_reviewed": np.zeros(N, np.int64), "sum_decision": np.zeros(N, np.int64),
                                    "sum_reviewed_decision": np.zeros(N, np.int64),
                                    "sum_reviewed_disagreement": np.zeros(N, np.int64),
                                    "sum_reviewed_deferred": np.zeros(N, np.int64)}
                    A_ = acc[key]
                    A_["n_seeds_reviewed"] += rev
                    A_["sum_decision"] += fin
                    A_["sum_reviewed_decision"] += rev * dec_rev
                    A_["sum_reviewed_disagreement"] += rev & disagree
                    A_["sum_reviewed_deferred"] += rev & deferred
                    # counts (integers; costs are formed from them, as in policy 1)
                    fp_old = int(((fin == 1) & leg & (old == 1)).sum())
                    fp_yng = int(((fin == 1) & leg & (old == 0)).sum())
                    fp = fp_old + fp_yng
                    fn = int(((fin == 0) & fraud).sum())
                    # split (section 6): reviewed-cases part and unreviewed-cases part, counts
                    r_fp = int(((dec_rev == 1) & leg & rev).sum()); r_fn = int(((dec_rev == 0) & fraud & rev).sum())
                    r_p1fp = int(((p1r == 1) & leg & rev).sum()); r_p1fn = int(((p1r == 0) & fraud & rev).sum())
                    u_fp = int((leg & ~rev).sum()); u_fn = 0
                    u_p1fp = int(((p1r == 1) & leg & ~rev).sum()); u_p1fn = int(((p1r == 0) & fraud & ~rev).sum())
                    nrev = int(rev.sum())
                    n_acc_rev = int(((dec_rev == 0) & rev).sum())
                    n_diff_clf = int(((dec_rev != p1r) & rev).sum())
                    n_dis = int((disagree & rev).sum())
                    n_def = int((deferred & rev).sum())
                    rc_leg = int((cell_c & rev & leg).sum()) if team == "C" else 0
                    rc_fr = int((cell_c & rev & fraud).sum()) if team == "C" else 0
                    rl_old = int((leg & (old == 1) & rev).sum()); rl_yng = int((leg & (old == 0) & rev).sum())
                    rfp_old = int(((dec_rev == 1) & leg & (old == 1) & rev).sum())
                    rfp_yng = int(((dec_rev == 1) & leg & (old == 0) & rev).sum())
                    fpr_old = fp_old / n_leg_old
                    fpr_yng = fp_yng / n_leg_yng
                    for lam in CH.LAMBDAS:
                        total = lam * fp + fn
                        p1_total = lam * p1_fp + p1_fn
                        rev_part = (lam * r_fp + r_fn) - (lam * r_p1fp + r_p1fn)
                        unrev_part = (lam * u_fp + u_fn) - (lam * u_p1fp + u_p1fn)
                        la_p1 = ((lam * r_p1fp + r_p1fn) - (lam * r_fp + r_fn)) / nrev if nrev else np.nan
                        la_rej = ((lam * int((leg & rev).sum())) - (lam * r_fp + r_fn)) / nrev if nrev else np.nan
                        cell_rows.append({
                            "seed": s, "team": team, "version": v, "capacity_label": cap["label"],
                            "capacity": cap["value"], "capacity_fraction": f"{cap['frac'].numerator}/{cap['frac'].denominator}",
                            "K": K, "realistic_range": cap["label"] in CH.REALISTIC, "lambda": lam, "is_anchor": lam == CH.ANCHOR,
                            "expected_loss_total": total, "expected_loss_per_case": total / N,
                            "regulatory_exposure_accepted_frauds_count": fn,
                            "regulatory_exposure_miss_rate": fn / n_fraud,
                            "regulatory_exposure_share_stopped": 1 - fn / n_fraud,
                            "false_rejections_count": fp, "false_rejections_50_plus": fp_old, "false_rejections_under_50": fp_yng,
                            "false_positive_rate_50_plus": fpr_old, "false_positive_rate_under_50": fpr_yng,
                            "overall_false_rejection_rate": fp / (n_leg_old + n_leg_yng),
                            "fairness_exposure_age_gap_signed": fpr_old - fpr_yng,
                            "fairness_exposure_age_gap_abs": abs(fpr_old - fpr_yng),
                            "policy_1_expected_loss_total": p1_total, "policy_1_accepted_frauds": p1_fn,
                            "difference_expected_loss_vs_policy_1": total - p1_total,
                            "reviewed_part_expected_loss": rev_part, "unreviewed_part_expected_loss": unrev_part,
                            "difference_accepted_frauds_vs_policy_1": fn - p1_fn,
                            "reviewed_part_accepted_frauds": r_fn - r_p1fn, "unreviewed_part_accepted_frauds": u_fn - u_p1fn,
                            "n_reviewed": nrev, "n_beyond_capacity": N - nrev,
                            "load": (N / K) if K else np.nan,
                            "load_one_over_capacity": (1 / cap["value"]) if K else np.nan,
                            "share_beyond_capacity": (N - K) / N,
                            "override_rate_accepted": n_acc_rev / nrev if nrev else np.nan,
                            "override_rate_differs_from_classifier": n_diff_clf / nrev if nrev else np.nan,
                            "n_reviewed_twin_classifier_disagree": n_dis,
                            "team_b_n_deferred": n_def if team == "B" else np.nan,
                            "team_b_share_disagreements_deferred": (n_def / n_dis if n_dis else np.nan) if team == "B" else np.nan,
                            "rule_c_changes_legitimate": rc_leg if team == "C" else np.nan,
                            "rule_c_changes_fraud": rc_fr if team == "C" else np.nan,
                            "loss_avoided_per_review_vs_policy_1": la_p1,
                            "loss_avoided_per_review_vs_rejection": la_rej,
                            "subgroup_disparity_reviewed": (rfp_old / rl_old - rfp_yng / rl_yng) if (rl_old and rl_yng) else np.nan,
                            "run_id": "this run"})
    p2_team_cases = pd.concat(master_rows, ignore_index=True)
    p2_cell_measures = pd.DataFrame(cell_rows)
    A.check(len(p2_team_cases) == 334275 and len(p2_cell_measures) == 6600 and len(p2_allocation) == 22285, "row counts of the replay")
    A.check(all(build_tests.values()), "build tests of the replay", **build_tests)

    seed_rows = []
    for (team, v, ci), A_ in acc.items():
        cap = caps[ci]
        seed_rows.append(pd.DataFrame({
            "team": team, "version": v, "capacity_label": cap["label"], "capacity": cap["value"], "K": cap["K"],
            "case_id": case_id, "n_seeds_reviewed": A_["n_seeds_reviewed"], "sum_decision": A_["sum_decision"],
            "sum_reviewed_decision": A_["sum_reviewed_decision"],
            "sum_reviewed_disagreement": A_["sum_reviewed_disagreement"],
            "sum_reviewed_deferred": A_["sum_reviewed_deferred"],
            "mean_decision": A_["sum_decision"] / len(CH.SEEDS), "mean_reviewed_share": A_["n_seeds_reviewed"] / len(CH.SEEDS)}))
    p2_seed_avg = pd.concat(seed_rows, ignore_index=True)
    A.check(len(p2_seed_avg) == 1470810, "row count of the seed sums")


    files = {}
    for df, name in ((p2_allocation, "p2_allocation.csv"), (p2_cell_measures, "p2_cell_measures.csv"),
                     (p2_team_cases, "p2_team_cases.parquet"), (p2_seed_avg, "p2_seed_avg_per_case.parquet")):
        path = os.path.join(a.out, name)
        if name.endswith(".parquet"):
            df.to_parquet(path, index=False)
        else:
            df.to_csv(path, index=False, float_format="%.17g")
        files[name] = C.sha256(path)
    C.write_record(a, {"step": a.step, "team_versions_slot_order": {str(k): v for k, v in teams.items()},
                       "p2m_item5": p2m5, "per_seed": {str(s): seed_info[s] for s in CH.SEEDS},
                       "build_tests": build_tests, "policy_1": {"false_rejections": p1_fp, "accepted_frauds": p1_fn},
                       "counts": {"n_cases": N, "n_frauds": n_fraud, "n_legitimate_50_plus": n_leg_old,
                                  "n_legitimate_under_50": n_leg_yng},
                       "calls": {"review_order": CH.CALL_ORDER, "dealing": CH.CALL_SLOT, "deference_draws": CH.CALL_DRAW},
                       "outputs_sha256": files})


if __name__ == "__main__":
    main()

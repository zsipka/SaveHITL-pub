"""Step: policy 3 (analyst-aware deferral), routing, replay, costing, the measures, the access-by-age counts for both
policies, the point figures of P3-T8, on the five drawn teams.

The rules, implemented once, alert by alert (the study's replay script, unchanged):
  routing (A and B share one; C has its own), per team version r, seed s and capacity K: alerts taken in the seed's
    review order (policy 2's call, RandomState(s).permutation(4457));
    team C only: aged 50 or over AND h >= 0.5  -> classifier (team C test), pool unchanged;
    pool has no room (reviewed so far >= K)    -> classifier;
    best reviewer = highest own score; tie: fewest alerts so far, then lower slot;
    best reviewer's score STRICTLY above the classifier's confidence -> that reviewer reviews (pool down by one);
    otherwise (equal included)                 -> classifier.
  scores: table shuffle_<s>#drawn_<r> of the router's month-7 predictions: own score per reviewer, and the classifier's
    confidence max(h, 1 - h); exact float64 comparison, no tolerance.
  final decision: classifier -> policy 1's decision (h >= 0.5); reviewer -> team rule: A the reviewer's own decision;
    B agree -> the shared decision, disagree -> classifier's if the deference draw (RandomState(100 + s).rand(4457)) is
    strictly below 0.8, else the reviewer's; C the reviewer's own decision.
Decisions: 1 = alert confirmed (application rejected), 0 = alert dismissed (application accepted).

Outputs: p3_routing_summary.csv, p3_cell_measures.csv, p3_access_by_age.csv, p3_t8_point_figures.csv,
         p3_routing.parquet, p3_team_cases.parquet, p3_seed_avg_per_case.parquet.
"""
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

from . import _chain as CH
from . import _common as C

N = CH.N


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    t0 = time.time()
    a = C.args([("--policy1", {"required": True}), ("--generator", {"required": True}), ("--draw", {"required": True}),
                ("--predict", {"required": True}), ("--policy2", {"required": True})])
    A = C.Asserts(a)
    preds = pd.read_pickle(CH.step_output(A, a.predict, "p3_router_month7_predictions.pkl"))
    p1 = CH.load_p1(A, a.policy1)
    case_id = p1["case_id"].to_numpy()
    y = p1["label_fraud"].to_numpy().astype(np.int64)
    old = p1["age_50_plus"].to_numpy().astype(np.int64)
    p1r = p1["p1_reject"].to_numpy().astype(np.int64)
    h = p1["classifier_score"].to_numpy()
    A.check(np.array_equal(p1r, (h >= 0.5).astype(np.int64)), "policy 1's decision equals h >= 0.5")
    twins = CH.load_twins(A, a.L, a.generator, (CH.TEST_MONTH,)).sort_index()
    A.check(np.array_equal(twins.index.to_numpy(), case_id) and bool(twins.notna().all().all()),
            "reviewers' alerts equal policy 1's, no missing decision")
    col_of = {n: j for j, n in enumerate(twins.columns)}
    TW = twins.to_numpy().astype(np.int64)
    teams = CH.load_teams(A, a.draw)
    caps = CH.capacities()
    p2rec = json.load(open(os.path.join(a.policy2, "record.json")))
    A.check({int(k): v for k, v in p2rec["team_versions_slot_order"].items()} == teams, "policy 2's team versions equal the draw's")
    p2m = pd.read_parquet(CH.step_output(A, a.policy2, "p2_team_cases.parquet"))
    leg, fraud = y == 0, y == 1
    n_leg_old, n_leg_yng, n_fraud = int((leg & (old == 1)).sum()), int((leg & (old == 0)).sum()), int(fraud.sum())
    p1_fp, p1_fn = int(((p1r == 1) & leg).sum()), int(((p1r == 0) & fraud).sum())
    testC = (old == 1) & (h >= 0.5)                 # team C's test; same h as p1_reject

    # policy 2's final decisions per (team, version, seed): review_rank and decision_if_reviewed, ordered by case_id
    p2_rank, p2_dec = {}, {}
    for (s, team, v), g in p2m.groupby(["seed", "team", "version"]):
        g = g.sort_values("case_id")
        assert np.array_equal(g["case_id"].to_numpy(), case_id)
        p2_rank[(int(s), team, int(v))] = g["review_rank"].to_numpy()
        p2_dec[(int(s), team, int(v))] = g["decision_if_reviewed"].to_numpy().astype(np.int64)
    del p2m

    # ------------------------------------------------------------------ order and draws, policy 2's exact calls
    order_of, draw_of, rank_of, seed_info = {}, {}, {}, {}
    alloc = pd.read_csv(CH.step_output(A, a.policy2, "p2_allocation.csv"), float_precision="round_trip")
    for s in CH.SEEDS:
        order, _ = CH.draw_allocation(s)
        d = CH.draw_deference(s)
        rank = np.empty(N, dtype=np.int64); rank[order] = np.arange(N)
        al = alloc[alloc["seed"] == s].sort_values("case_id")
        A.check(np.array_equal(al["review_rank"].to_numpy(), rank) and np.array_equal(al["deference_draw"].to_numpy(), d),
                "review order and deference draws equal to policy 2's", seed=s)
        order_of[s], draw_of[s], rank_of[s] = order, d, rank
        osha = sha256_bytes(order.astype("<i8").tobytes()); dsha = sha256_bytes(d.astype("<f8").tobytes())
        seed_info[s] = {"order_sha256_int64": osha, "draw_sha256_float64": dsha,
                        "equal_to_policy_2_record": bool(p2rec["per_seed"][str(s)]["order_sha256_int64"] == osha
                                                         and p2rec["per_seed"][str(s)]["draw_sha256_float64"] == dsha)}
        A.check(seed_info[s]["equal_to_policy_2_record"], "order and draw checksums equal to policy 2's record", seed=s)

    STEP = {0: "expert", 1: "classifier: best expert not strictly above", 2: "classifier: pool full", 3: "classifier: team C test"}


    def route(order, E, c, is_test, K):
        """One routing, alert by alert (trees of section 2.1). E: N x 10 own scores (slot order), c: confidences."""
        Er = E.tolist(); cr = c.tolist(); tr = is_test.tolist()
        dm = np.full(N, -1, dtype=np.int8)
        step = np.zeros(N, dtype=np.int8)
        nby = [0] * 10
        used = 0
        ties = {"experts_tied_resolved_by_fewest": 0, "experts_tied_resolved_by_slot": 0,
                "best_expert_equal_to_classifier": 0}
        for i in order.tolist():
            if tr[i]:
                step[i] = 3; continue
            if used >= K:
                step[i] = 2; continue
            row = Er[i]
            m = max(row)
            cand = [j for j in range(10) if row[j] == m]
            if len(cand) > 1:
                f = min(nby[j] for j in cand)
                c2 = [j for j in cand if nby[j] == f]
                if len(c2) == 1:
                    ties["experts_tied_resolved_by_fewest"] += 1
                else:
                    ties["experts_tied_resolved_by_slot"] += 1
                j = c2[0]
            else:
                j = cand[0]
            if m > cr[i]:
                dm[i] = j; nby[j] += 1; used += 1; step[i] = 0
            else:
                if m == cr[i]:
                    ties["best_expert_equal_to_classifier"] += 1
                step[i] = 1
        return dm, step, nby, ties


    def tree(team, twin, p1dec, draw):
        """Final decision on an alert sent to an expert (section 2.1)."""
        if team == "A":
            return twin.copy()
        if team == "B":
            return np.where(twin == p1dec, twin, np.where(draw < CH.DEFER_P, p1dec, twin))
        if team == "C":
            return twin.copy()
        raise ValueError(team)


    def cost(dec, lam):
        return lam * ((dec == 1) & leg) + ((dec == 0) & fraud)


    # ------------------------------------------------------------------ routing
    routing_parts, summary_rows = [], []
    routes = {}
    for s in CH.SEEDS:
        for r in CH.VERSIONS:
            tb = preds[CH.setup_name(r, s)]
            assert np.array_equal(tb.index.to_numpy(), case_id)
            members = teams[r]
            E = tb[members].to_numpy(dtype=np.float64)
            c = tb["classifier_h"].to_numpy(dtype=np.float64)
            best = E.max(axis=1)
            for rt, is_test in (("AB", np.zeros(N, dtype=bool)), ("C", testC)):
                n_elig = int(((best > c) & ~is_test).sum())
                for ci, cap in enumerate(caps):
                    K = cap["K"]
                    dm, step, nby, ties = route(order_of[s], E, c, is_test, K)
                    routes[(rt, r, s, ci)] = (dm, step)
                    nrev = int((dm >= 0).sum())
                    summary_rows.append({"routing": rt, "version": r, "seed": s, "router_table": CH.setup_name(r, s),
                                         "capacity_label": cap["label"], "capacity": cap["value"], "K": K,
                                         "n_eligible": n_elig, "n_reviewed": nrev, "n_to_classifier": N - nrev,
                                         "n_team_c_test": int(is_test.sum()) if rt == "C" else 0,
                                         "n_classifier_not_beaten": int((step == 1).sum()), "n_classifier_pool_full": int((step == 2).sum()),
                                         **{f"n_slot_{j}": nby[j] for j in range(10)},
                                         **{f"twin_slot_{j}": members[j] for j in range(10)},
                                         **{f"ties_{k}": v for k, v in ties.items()},
                                         "load": nrev / K if K else np.nan,
                                         "decision_maker_sha256_int8": sha256_bytes(dm.tobytes())})
                    routing_parts.append(pd.DataFrame({
                        "routing": rt, "version": np.int8(r), "seed": np.int8(s), "capacity_label": cap["label"],
                        "K": np.int16(K), "case_id": case_id.astype(np.int32), "review_position": rank_of[s].astype(np.int16),
                        "decision_maker_slot": dm, "route_step": step}))
    t_route = round(time.time() - t0, 3)
    routing = pd.concat(routing_parts, ignore_index=True)
    del routing_parts
    names_by_version = {r: teams[r] for r in CH.VERSIONS}
    routing["routing"] = routing["routing"].astype("category")
    routing["capacity_label"] = routing["capacity_label"].astype("category")
    dm_name = np.empty(len(routing), dtype=object)
    slots = routing["decision_maker_slot"].to_numpy(); vers = routing["version"].to_numpy()
    dm_name[:] = "classifier"
    for r in CH.VERSIONS:
        for j in range(10):
            dm_name[(vers == r) & (slots == j)] = teams[r][j]
    routing["decision_maker"] = pd.Categorical(dm_name)
    routing["route_step"] = pd.Categorical.from_codes(routing["route_step"].to_numpy(), categories=[STEP[k] for k in range(4)])
    del dm_name

    # ------------------------------------------------------------------ replay, costing, measures
    master_parts, cell_rows, t8_rows, acc_rows = [], [], [], []
    acc = {}
    for s in CH.SEEDS:
        d = draw_of[s]
        for team in CH.TEAMS:
            rt = "C" if team == "C" else "AB"
            for r in CH.VERSIONS:
                members = teams[r]
                jcol = np.array([col_of[m] for m in members])
                tb = preds[CH.setup_name(r, s)]
                E = tb[members].to_numpy(dtype=np.float64)
                for ci, cap in enumerate(caps):
                    K = cap["K"]
                    dm, step = routes[(rt, r, s, ci)]
                    rev = dm >= 0
                    twin_dm = np.where(rev, TW[np.arange(N), jcol[np.where(rev, dm, 0)]], -1)
                    dec_rev = tree(team, np.where(rev, twin_dm, 0), p1r, d)
                    fin = np.where(rev, dec_rev, p1r)
                    master_parts.append(pd.DataFrame({
                        "seed": np.int8(s), "team": team, "version": np.int8(r), "capacity_label": cap["label"], "K": np.int16(K),
                        "case_id": case_id.astype(np.int32), "decision_maker_slot": dm, "twin_decision": twin_dm.astype(np.int8),
                        "final_decision": fin.astype(np.int8)}))
                    # policy 2, same team, version, seed and capacity
                    rk, dr = p2_rank[(s, team, r)], p2_dec[(s, team, r)]
                    p2rev = rk < K
                    p2fin = np.where(p2rev, dr, 1)
                    # seed sums for the (later) bootstrap
                    key = (team, r, ci)
                    if key not in acc:
                        acc[key] = {k: np.zeros(N, np.int64) for k in (
                            "n_seeds_reviewed", "sum_decision", "sum_reviewed_decision", "sum_reviewed_disagreement",
                            "sum_reviewed_deferred", "sum_reviewed_twin_right_p1_wrong", "sum_reviewed_twin_wrong_p1_right",
                            "sum_p2_decision", "sum_p2_decision_on_p3_reviewed", "sum_p2_reviewed")}
                    A_ = acc[key]
                    disagree = rev & (twin_dm != p1r)
                    deferred = disagree & (d < CH.DEFER_P) if team == "B" else np.zeros(N, dtype=bool)
                    tw_right = rev & (twin_dm == y); p1_right = (p1r == y)
                    A_["n_seeds_reviewed"] += rev; A_["sum_decision"] += fin; A_["sum_reviewed_decision"] += rev * fin
                    A_["sum_reviewed_disagreement"] += disagree; A_["sum_reviewed_deferred"] += deferred
                    A_["sum_reviewed_twin_right_p1_wrong"] += tw_right & ~p1_right
                    A_["sum_reviewed_twin_wrong_p1_right"] += rev & ~tw_right & p1_right
                    A_["sum_p2_decision"] += p2fin; A_["sum_p2_decision_on_p3_reviewed"] += rev * p2fin; A_["sum_p2_reviewed"] += p2rev
                    # access to a reviewer by age group, both policies
                    for pol, sent in (("policy 3", rev), ("policy 2", p2rev)):
                        for ag in (1, 0):
                            for cd in (1, 0):
                                g = (old == ag) & (p1r == cd)
                                acc_rows.append({"policy": pol, "team": team, "version": r, "seed": s, "capacity_label": cap["label"],
                                                 "capacity": cap["value"], "K": K, "age_group": "50 or over" if ag else "under 50",
                                                 "classifier_decision": "confirm" if cd else "dismiss",
                                                 "n_alerts": int(g.sum()), "n_sent_to_reviewer": int((g & sent).sum())})
                    # counts
                    fp_old = int(((fin == 1) & leg & (old == 1)).sum()); fp_yng = int(((fin == 1) & leg & (old == 0)).sum())
                    fp = fp_old + fp_yng; fn = int(((fin == 0) & fraud).sum())
                    q_fp_old = int(((p2fin == 1) & leg & (old == 1)).sum()); q_fp_yng = int(((p2fin == 1) & leg & (old == 0)).sum())
                    q_fp = q_fp_old + q_fp_yng; q_fn = int(((p2fin == 0) & fraud).sum())
                    nrev = int(rev.sum())
                    n_acc_rev = int(((fin == 0) & rev).sum()); n_diff_clf = int(((fin != p1r) & rev).sum())
                    n_dis = int(disagree.sum()); n_def = int(deferred.sum())
                    rl_old = int((leg & (old == 1) & rev).sum()); rl_yng = int((leg & (old == 0) & rev).sum())
                    rfp_old = int(((fin == 1) & leg & (old == 1) & rev).sum()); rfp_yng = int(((fin == 1) & leg & (old == 0) & rev).sum())
                    rule_c = int((rev & (old == 1) & (twin_dm == 0) & (p1r == 1)).sum()) if team == "C" else np.nan
                    score_rev = E[np.arange(N), np.where(rev, dm, 0)]
                    fpr_old, fpr_yng = fp_old / n_leg_old, fp_yng / n_leg_yng
                    q_fpr_old, q_fpr_yng = q_fp_old / n_leg_old, q_fp_yng / n_leg_yng
                    for lam in CH.LAMBDAS:
                        c3, c2, c1 = cost(fin, lam), cost(p2fin, lam), cost(p1r, lam)
                        total, p2_total, p1_total = float(c3.sum()), float(c2.sum()), float(c1.sum())
                        clf_part = float((c3 - c2)[~rev].sum()); rev_part = float((c3 - c2)[rev].sum())
                        la_p1 = float((c1 - c3)[rev].sum()) / nrev if nrev else np.nan
                        la_rej = float((cost(np.ones(N, np.int64), lam) - c3)[rev].sum()) / nrev if nrev else np.nan
                        cell_rows.append({
                            "seed": s, "team": team, "version": r, "capacity_label": cap["label"], "capacity": cap["value"],
                            "capacity_fraction": f"{cap['frac'].numerator}/{cap['frac'].denominator}", "K": K,
                            "realistic_range": cap["label"] in CH.REALISTIC, "lambda": lam, "is_anchor": lam == CH.ANCHOR,
                            "router_table": CH.setup_name(r, s),
                            "expected_loss_total": total, "expected_loss_per_case": total / N,
                            "regulatory_exposure_accepted_frauds_count": fn, "regulatory_exposure_miss_rate": fn / n_fraud,
                            "regulatory_exposure_share_stopped": 1 - fn / n_fraud,
                            "false_rejections_count": fp, "false_rejections_50_plus": fp_old, "false_rejections_under_50": fp_yng,
                            "false_positive_rate_50_plus": fpr_old, "false_positive_rate_under_50": fpr_yng,
                            "overall_false_rejection_rate": fp / (n_leg_old + n_leg_yng),
                            "fairness_exposure_age_gap_signed": fpr_old - fpr_yng, "fairness_exposure_age_gap_abs": abs(fpr_old - fpr_yng),
                            "policy_1_expected_loss_total": p1_total, "policy_1_accepted_frauds": p1_fn,
                            "difference_expected_loss_vs_policy_1": total - p1_total,
                            "difference_accepted_frauds_vs_policy_1": fn - p1_fn,
                            "policy_2_expected_loss_total": p2_total, "policy_2_accepted_frauds": q_fn,
                            "policy_2_overall_false_rejection_rate": q_fp / (n_leg_old + n_leg_yng),
                            "policy_2_fairness_exposure_age_gap_abs": abs(q_fpr_old - q_fpr_yng),
                            "difference_expected_loss_vs_policy_2": total - p2_total,
                            "classifier_part_expected_loss_vs_policy_2": clf_part, "reviewed_part_expected_loss_vs_policy_2": rev_part,
                            "difference_accepted_frauds_vs_policy_2": fn - q_fn,
                            "classifier_part_accepted_frauds_vs_policy_2": int(((fin == 0) & fraud & ~rev).sum()) - int(((p2fin == 0) & fraud & ~rev).sum()),
                            "reviewed_part_accepted_frauds_vs_policy_2": int(((fin == 0) & fraud & rev).sum()) - int(((p2fin == 0) & fraud & rev).sum()),
                            "n_reviewed": nrev, "n_to_classifier": N - nrev, "load": nrev / K if K else np.nan,
                            "override_rate_accepted": n_acc_rev / nrev if nrev else np.nan,
                            "override_rate_differs_from_classifier": n_diff_clf / nrev if nrev else np.nan,
                            "n_reviewed_twin_classifier_disagree": n_dis,
                            "team_b_n_deferred": n_def if team == "B" else np.nan,
                            "team_b_share_disagreements_deferred": (n_def / n_dis if n_dis else np.nan) if team == "B" else np.nan,
                            "rule_c_changes_on_reviewed": rule_c,
                            "loss_avoided_per_review_vs_policy_1": la_p1, "loss_avoided_per_review_vs_rejection": la_rej,
                            "subgroup_disparity_reviewed": (rfp_old / rl_old - rfp_yng / rl_yng) if (rl_old and rl_yng) else np.nan,
                            "criterion_1_share_expert_right_policy_1_wrong": int((tw_right & ~p1_right).sum()) / nrev if nrev else np.nan,
                            "criterion_1_share_expert_wrong_policy_1_right": int((rev & ~tw_right & p1_right).sum()) / nrev if nrev else np.nan,
                            "min_margin_reviewer_over_classifier": float((score_rev - tb["classifier_h"].to_numpy())[rev].min()) if nrev else np.nan,
                            "run_id": "this run"})
                        # P3-T8 (section 8.2): on the alerts policy 2 confirms without review, at capacity 0.75, teams B and C
                        if cap["label"] == "0.75" and team in ("B", "C") and lam in (CH.ANCHOR,):
                            un = ~p2rev
                            t8_rows.append({"team": team, "version": r, "seed": s, "capacity_label": "0.75", "K": K,
                                            "n_alerts_policy_2_confirms_unreviewed": int(un.sum()),
                                            "difference_expected_loss_0.057_on_those_alerts": float((c3 - c2)[un].sum()),
                                            "difference_accepted_frauds_on_those_alerts": int(((fin == 0) & fraud & un).sum()) - int(((p2fin == 0) & fraud & un).sum()),
                                            "run_id": "this run"})
    t_replay = round(time.time() - t0, 3)
    master = pd.concat(master_parts, ignore_index=True)
    del master_parts
    master["team"] = master["team"].astype("category"); master["capacity_label"] = master["capacity_label"].astype("category")
    cells = pd.DataFrame(cell_rows)
    summary = pd.DataFrame(summary_rows)
    access = pd.DataFrame(acc_rows)
    t8 = pd.DataFrame(t8_rows)
    t8_mean_seed = t8.groupby(["team", "version"], as_index=False)[[
        "difference_expected_loss_0.057_on_those_alerts", "difference_accepted_frauds_on_those_alerts"]].mean()
    t8_mean_seed["seed"] = "mean of 5 seeds"
    t8_mean_v = t8_mean_seed.groupby("team", as_index=False)[[
        "difference_expected_loss_0.057_on_those_alerts", "difference_accepted_frauds_on_those_alerts"]].mean()
    t8_mean_v["version"] = "mean of 5 versions"; t8_mean_v["seed"] = "mean of 5 seeds"
    t8_out = pd.concat([t8, t8_mean_seed, t8_mean_v], ignore_index=True)
    seed_rows = []
    for (team, r, ci), A_ in acc.items():
        cap = caps[ci]
        seed_rows.append(pd.DataFrame({"team": team, "version": r, "capacity_label": cap["label"], "capacity": cap["value"],
                                       "K": cap["K"], "case_id": case_id, **A_,
                                       "mean_decision": A_["sum_decision"] / 5, "mean_reviewed_share": A_["n_seeds_reviewed"] / 5}))
    seed_avg = pd.concat(seed_rows, ignore_index=True)
    A.check(len(routing) == 1100 * N and len(master) == 1650 * N and len(cells) == 6600 and len(seed_avg) == 330 * N
            and len(access) == 2 * 1650 * 4 and len(summary) == 1100, "row counts of the routing and replay")
    # build tests (arithmetic of section 2.2, not the check P3-C1): parts add up to the whole difference
    bt = {"split_vs_policy_2_adds_up_expected_loss": float((cells["classifier_part_expected_loss_vs_policy_2"] + cells["reviewed_part_expected_loss_vs_policy_2"] - cells["difference_expected_loss_vs_policy_2"]).abs().max()),
          "split_vs_policy_2_adds_up_accepted_frauds": int((cells["classifier_part_accepted_frauds_vs_policy_2"] + cells["reviewed_part_accepted_frauds_vs_policy_2"] - cells["difference_accepted_frauds_vs_policy_2"]).abs().max()),
          "capacity_0_equals_policy_1": bool((cells.loc[cells.K == 0, "difference_expected_loss_vs_policy_1"].abs() < 1e-12).all())}
    A.check(bt["split_vs_policy_2_adds_up_expected_loss"] < 1e-9 and bt["split_vs_policy_2_adds_up_accepted_frauds"] == 0
            and bt["capacity_0_equals_policy_1"], "build tests: parts add up; capacity 0 equals policy 1", **bt)


    files = {}
    for df, name in ((summary, "p3_routing_summary.csv"), (cells, "p3_cell_measures.csv"), (access, "p3_access_by_age.csv"),
                     (t8_out, "p3_t8_point_figures.csv"), (routing, "p3_routing.parquet"), (master, "p3_team_cases.parquet"),
                     (seed_avg, "p3_seed_avg_per_case.parquet")):
        path = os.path.join(a.out, name)
        if name.endswith(".parquet"):
            df.to_parquet(path, index=False)
        else:
            df.to_csv(path, index=False, float_format="%.17g")
        files[name] = C.sha256(path)
    C.write_record(a, {"step": a.step, "route_steps": STEP, "per_seed": seed_info, "build_tests": bt,
                       "runtime_routing_s": t_route, "runtime_replay_s": round(t_replay - t_route, 3),
                       "outputs_sha256": files})


if __name__ == "__main__":
    main()

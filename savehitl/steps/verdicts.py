"""Step: the verdicts of policy 2 (--policy 2) or policy 3 (--policy 3), from the bootstrap's exported intervals.

Turns the intervals into the verdicts and rule outcomes fixed in the design: the verdict words (lower end above 0 "does
worse", upper end below 0 "beats", otherwise "no difference shown"; ends within 1e-9 of 0 count as 0), the five-version
rule, the deciding results with their labels, the rule outcomes, the capacity boundaries, the descriptive verdicts and
cost-ratio labels, the chance count and the bias-by-capacity readings. Reads the bootstrap's interval file exactly
(every cell as text, numbers by Python's float() of the text); computes no interval. The computation is the study's
verdict script and its rules module (`savehitl.boot.verdict_rules`), unchanged.

Outputs: p<k>_verdict_deciding.csv, _rules.csv, _descriptive.csv, _cost_ratio_labels.csv, _boundaries.csv, _chance.csv,
_bias_x_capacity.csv.
"""
import json
import os

import numpy as np
import pandas as pd

from ..boot import verdict_rules as VR
from . import _chain as CH
from . import _common as C

MEAN = "mean of 5 versions"
VERS = ["1", "2", "3", "4", "5"]
TEAMS = ("A", "B", "C")
LAMS = (0.035, 0.0537, 0.057, 0.171)
REALISTIC = ("0.65", "0.70", "0.75", "0.80", "0.85", "0.90", "10/11", "0.95", "1.00")
DEC_MEASURES = (("difference_expected_loss", "0.057"), ("difference_accepted_frauds", ""), ("difference_age_gap_abs", ""))
MNAME = {"difference_expected_loss": "expected loss", "difference_accepted_frauds": "accepted frauds",
         "difference_age_gap_abs": "absolute age gap", "difference_age_gap_signed": "signed age gap"}


def main():
    a = C.args([("--policy", {"type": int, "required": True, "choices": [2, 3]}), ("--policy1", {"required": True}),
                ("--replay", {"required": True, "help": "this policy's replay step folder"}),
                ("--boot-record", {"required": True}), ("--boot-intervals", {"required": True}),
                ("--p2u-over", {"required": True, "choices": ["all", "non-anchor"],
                                 "help": "the run passes non-anchor (0.035, 0.0537, 0.171); no default"})])
    A = C.Asserts(a)
    P = a.policy
    pre = f"p{P}"
    bm = json.load(open(a.boot_record))
    A.check(bool(bm.get("build_tests", {}).get("pass")), "the bootstrap passed its build tests")
    ipath = a.boot_intervals
    iname = f"{pre}_boot_intervals.csv"
    want = bm.get("outputs_sha256", {}).get(iname) or bm.get("exports", {}).get(iname, {}).get("sha256")
    A.check(want is not None and C.sha256(ipath) == want, "interval file equal to the checksum its bootstrap recorded")
    NUMERIC_COLS = ("policy", "K", "point_estimate", "percentile_low", "percentile_high", "ci_low", "ci_high",
                    "resamples_used", "resamples_dropped")
    iv = pd.read_csv(ipath, dtype=str, keep_default_na=False)
    miss_cols = [c for c in NUMERIC_COLS if c not in iv.columns]
    if miss_cols:
        A.check(False, "bootstrap export holds every numeric column", missing=miss_cols)
    for c in NUMERIC_COLS:
        iv[c] = np.array([np.nan if x == "" else float(x) for x in iv[c].tolist()], dtype=np.float64)
    iv["lambda"] = iv["lambda"].map(lambda x: "" if x == "" else repr(float(x)))
    G3 = int(bm["bootstrap"]["g3_dropped_resamples"])
    g3_withhold = G3 > VR.G3_LIMIT
    N_DEC = 61 if P == 2 else 66
    IDX = {(r.comparison, r.team, r.version, r.capacity_label, r.measure, r["lambda"], r.level): r for _, r in iv.iterrows()}


    def row(comp, team, ver, cap, meas, lam, level="95%"):
        return IDX[(comp, team, ver, cap, meas, lam, level)]


    def vword(r):
        return VR.verdict(r.ci_low, r.ci_high)


    # ------------------------------------------------------------------ policy 1 and per-seed figures (seed ranges)
    case_id, label, age50, p1 = CH.load_p1_arrays(A, a.policy1)
    leg = label == 0
    p1_gap = ((p1 == 1) & leg & (age50 == 1)).sum() / (leg & (age50 == 1)).sum() - ((p1 == 1) & leg & (age50 == 0)).sum() / (leg & (age50 == 0)).sum()
    p1_frr = ((p1 == 1) & leg).sum() / leg.sum()
    cpath = CH.step_output(A, a.replay, f"p{P}_cell_measures.csv")
    cl = pd.read_csv(cpath, float_precision="round_trip", dtype={"capacity_label": str})
    cl["version"] = cl["version"].astype(str)
    cl["lam"] = cl["lambda"].map(lambda x: repr(float(x)))
    cl["abs_gap"] = cl["fairness_exposure_age_gap_signed"].abs()
    CL = {k: g.set_index("seed") for k, g in cl.groupby(["team", "version", "capacity_label", "lam"])}


    def per_seed(comp, team, ver, cap, meas, lam):
        """Per-seed point differences (policy 2 design section 6, 'Seeds'); None where not applicable."""
        L = lam if lam else "0.057"

        def one(v):
            g = CL[(team, v, cap, L)]
            if comp == "vs_policy_1":
                return {"difference_expected_loss": g["difference_expected_loss_vs_policy_1"],
                        "difference_accepted_frauds": g["difference_accepted_frauds_vs_policy_1"],
                        "difference_age_gap_abs": g["abs_gap"] - abs(p1_gap),
                        "difference_age_gap_signed": g["fairness_exposure_age_gap_signed"] - p1_gap}.get(meas)
            if comp == "vs_policy_2":
                return {"difference_expected_loss": g["difference_expected_loss_vs_policy_2"],
                        "difference_accepted_frauds": g["difference_accepted_frauds_vs_policy_2"],
                        "difference_age_gap_abs": g["abs_gap"] - g["policy_2_fairness_exposure_age_gap_abs"]}.get(meas)
            if comp in ("B_minus_A", "C_minus_A"):
                h = CL[("A", v, cap, L)]
                return {"difference_expected_loss": g["expected_loss_total"] - h["expected_loss_total"],
                        "difference_accepted_frauds": g["regulatory_exposure_accepted_frauds_count"] - h["regulatory_exposure_accepted_frauds_count"],
                        "difference_age_gap_abs": g["abs_gap"] - h["abs_gap"],
                        "difference_age_gap_signed": g["fairness_exposure_age_gap_signed"] - h["fairness_exposure_age_gap_signed"]}.get(meas)
            return None
        if ver == MEAN:
            xs = [one(v) for v in VERS]
            if any(x is None for x in xs):
                return None
            s = sum(xs) / 5.0
        else:
            s = one(ver)
        if s is None:
            return None
        return float(s.min()), float(s.max())


    # ------------------------------------------------------------------ deciding results (P<k>-T3)
    def deciding_spec():
        out = []
        for m, lam in DEC_MEASURES:
            out.append((1, "vs_policy_1", "A", "1.00", m, lam))
        for k, t in ((2, "B"), (3, "C")):
            for cap in REALISTIC:
                for m, lam in DEC_MEASURES:
                    out.append((k, "vs_policy_1", t, cap, m, lam))
        if P == 2:
            for m, lam in DEC_MEASURES:
                out.append((4, "B_minus_A", "B", "0.75", m, lam))
            out.append((5, "C_minus_A", "C", "0.75", "difference_expected_loss", "0.057"))
        else:
            for k, t, cap in ((4, "A", "1.00"), (5, "B", "0.75"), (6, "C", "0.75")):
                for m, lam in DEC_MEASURES:
                    out.append((k, "vs_policy_2", t, cap, m, lam))
        return out


    spec = deciding_spec()
    assert len(spec) == N_DEC
    dec_rows = []
    for (k, comp, t, cap, m, lam) in spec:
        rm = row(comp, t, MEAN, cap, m, lam, "adjusted")
        vv = [vword(row(comp, t, v, cap, m, lam, "adjusted")) for v in VERS]
        mv = vword(rm)
        outcome, route = VR.five_version_outcome(vv, mv)
        if m == "difference_age_gap_abs" and g3_withhold:
            outcome, route = VR.NOT_GIVEN_G3, "G3"
        labels = []
        rec = {"policy": P, "result_id": f"policy {P}, comparison {k}, {MNAME[m]}" + (f", capacity {cap}" if k in (2, 3) else ""),
               "comparison": k, "comparison_kind": comp, "team": t, "capacity_label": cap, "measure": m, "lambda": lam,
               "estimate_mean_of_5": rm.point_estimate, "adjusted_ci_low": rm.ci_low, "adjusted_ci_high": rm.ci_high,
               "percentile_low": rm.percentile_low, "percentile_high": rm.percentile_high, "verdict_mean_of_5": mv}
        for v, w in zip(VERS, vv):
            rv = row(comp, t, v, cap, m, lam, "adjusted")
            rec.update({f"v{v}_estimate": rv.point_estimate, f"v{v}_ci_low": rv.ci_low, f"v{v}_ci_high": rv.ci_high, f"v{v}_verdict": w})
        sr = per_seed(comp, t, MEAN, cap, m, lam)
        rec.update({"seed_min": sr[0] if sr else np.nan, "seed_max": sr[1] if sr else np.nan, "verdict": outcome, "verdict_route": route})
        # labels
        if P == 2 and k in (1, 2, 3) and m in ("difference_expected_loss", "difference_accepted_frauds"):
            part = "expected_loss" if m == "difference_expected_loss" else "accepted_frauds"
            rr = row("vs_policy_1", t, MEAN, cap, f"reviewed_part_{part}", lam)
            ur = row("vs_policy_1", t, MEAN, cap, f"unreviewed_part_{part}", lam)
            rec.update({"reviewed_part_point": rr.point_estimate, "reviewed_part_ci95_low": rr.ci_low, "reviewed_part_ci95_high": rr.ci_high,
                        "unreviewed_part_point": ur.point_estimate, "unreviewed_part_ci95_low": ur.ci_low, "unreviewed_part_ci95_high": ur.ci_high})
            if outcome == VR.WORSE:
                lb = VR.split_label(rr.ci_low, ur.ci_low)
                labels.append(lb)
                if cap == "1.00" and lb != VR.LBL_REVIEWERS:
                    rec["capacity_1_overflow_flag"] = "overflow label at capacity 1: flagged as a possible computation error; reported to the coordinator; not relabelled"
        if m == "difference_age_gap_abs" and k in (1, 2, 3):
            fr = row("vs_policy_1", t, MEAN, cap, "difference_overall_false_rejection_rate", "")
            team_frr = p1_frr + fr.point_estimate
            rec.update({"overall_false_rejection_rate_team": team_frr, "overall_false_rejection_rate_policy_1": p1_frr})
            if P == 2:
                if VR.age_property_p2(rm.point_estimate, fr.point_estimate):      # 1e-9 zero threshold
                    labels.append(VR.LBL_AGE_PROPERTY)
                if k == 2 and outcome == VR.WORSE:
                    labels.append(VR.LBL_AGE_P2R2)
        if P == 2 and k == 4:
            labels.append(VR.LBL_COMP4)
        if P == 3 and k in (5, 6) and m == "difference_age_gap_abs":
            fr = row("vs_policy_2", t, MEAN, cap, "difference_overall_false_rejection_rate", "")
            q = row("policy_2_side", t, MEAN, cap, "overall_false_rejection_rate", "")
            rec.update({"overall_false_rejection_rate_policy_3": q.point_estimate + fr.point_estimate,
                        "overall_false_rejection_rate_policy_2": q.point_estimate})
            for v in VERS:
                frv = row("vs_policy_2", t, v, cap, "difference_overall_false_rejection_rate", "")
                qv = row("policy_2_side", t, v, cap, "overall_false_rejection_rate", "")
                rec[f"v{v}_overall_false_rejection_rate_policy_3"] = qv.point_estimate + frv.point_estimate
                rec[f"v{v}_overall_false_rejection_rate_policy_2"] = qv.point_estimate
            # comparisons 5 and 6 only, mean of the five versions only, policy 2 side, signs reversed:
            # policy 2 closer to zero (P3 - P2 > 0 on |gap|) while policy 2's overall false rejection rate is higher
            if VR.age_property_p2_side(rm.point_estimate, fr.point_estimate):
                labels.append("policy 2 side: " + VR.LBL_AGE_PROPERTY)
        rec["labels"] = " | ".join(labels)
        dec_rows.append(rec)
    if P == 2:      # P2-K: comparison 5, accepted frauds and signed age gap, reported with intervals, by construction
        for m in ("difference_accepted_frauds", "difference_age_gap_signed"):
            rm = row("C_minus_A", "C", MEAN, "0.75", m, "", "adjusted")
            rec = {"policy": 2, "result_id": f"policy 2, comparison 5, {MNAME[m]} (P2-K)", "comparison": 5, "comparison_kind": "C_minus_A",
                   "team": "C", "capacity_label": "0.75", "measure": m, "lambda": "", "estimate_mean_of_5": rm.point_estimate,
                   "adjusted_ci_low": rm.ci_low, "adjusted_ci_high": rm.ci_high, "percentile_low": rm.percentile_low,
                   "percentile_high": rm.percentile_high, "verdict_mean_of_5": vword(rm), "verdict": VR.LBL_BY_CONSTRUCTION,
                   "verdict_route": "P2-K", "labels": VR.LBL_BY_CONSTRUCTION}
            for v in VERS:
                rv = row("C_minus_A", "C", v, "0.75", m, "", "adjusted")
                rec.update({f"v{v}_estimate": rv.point_estimate, f"v{v}_ci_low": rv.ci_low, f"v{v}_ci_high": rv.ci_high, f"v{v}_verdict": vword(rv)})
            dec_rows.append(rec)
    DEC = pd.DataFrame(dec_rows)


    # ------------------------------------------------------------------ rule outcomes
    def res(k, t, m, cap=None):
        q = DEC[(DEC.comparison == k) & (DEC.team == t) & (DEC.measure == m) & (DEC.verdict_route != "P2-K")]
        if cap is not None:
            q = q[q.capacity_label == cap]
        return q


    def g3(q, holds, trigger):
        """Rule outcome under G3: None if a withheld verdict could change it; with the withheld list."""
        out, nw = VR.g3_two_completions(holds, list(q.verdict), list(q.verdict_route == "G3"), trigger)
        return out, "; ".join(q[q.verdict_route == "G3"].result_id)


    def any_worse(vs):
        return any(v == VR.WORSE for v in vs)


    rules = []
    for m, lam in DEC_MEASURES:
        mn = MNAME[m]
        c1 = res(1, "A", m).iloc[0]
        if c1.verdict_route == "G3":          # P-R0 rests on one verdict per measure
            rules.append({"rule": f"P{P}-R0", "measure": mn, "outcome": VR.NOT_TESTABLE_G3,
                          "statement": f"comparison 1: {VR.NOT_TESTABLE_G3} on {mn}", "withheld_g3": c1.result_id})
        else:
            verb = {VR.WORSE: "does worse than", VR.BEATS: "beats"}.get(c1.verdict)
            rules.append({"rule": f"P{P}-R0", "measure": mn, "outcome": c1.verdict,
                          "statement": f"comparison 1: a standard team with full capacity {verb} automation on {mn}"
                          if verb else f"comparison 1: {c1.verdict} on {mn}", "withheld_g3": ""})
        if P == 2:
            c3 = res(3, "C", m); below1 = c3[c3.capacity_label != "1.00"]
            w3 = below1[below1.verdict == VR.WORSE]
            bsum3 = VR.interval_boundary(list(zip(c3.capacity_label, c3.verdict)))
            o, wh = g3(below1, any_worse, VR.WORSE)
            rules.append({"rule": "P2-R1", "measure": mn,
                          "outcome": VR.NOT_TESTABLE_G3 if o is None else ("supported on the measure" if o else "not supported on the measure"),
                          "capacities_does_worse": ", ".join(w3.capacity_label), "labels": " || ".join(f"{r.capacity_label}: {r.labels}" for r in w3.itertuples()),
                          "boundary_summary": bsum3["text"], "withheld_g3": wh})
            c2 = res(2, "B", m); w2 = c2[c2.verdict == VR.WORSE]
            bsum2 = VR.interval_boundary(list(zip(c2.capacity_label, c2.verdict)))
            o, wh = g3(c2, any_worse, VR.WORSE)
            rules.append({"rule": "P2-R2", "measure": mn,
                          "outcome": VR.NOT_TESTABLE_G3 if o is None else ("supported on the measure" if o else "not supported on the measure"),
                          "capacities_does_worse": ", ".join(w2.capacity_label), "labels": " || ".join(f"{r.capacity_label}: {r.labels}" for r in w2.itertuples()),
                          "boundary_summary": bsum2["text"],
                          "comparison_4": res(4, "B", m).iloc[0].verdict + " (" + VR.LBL_COMP4 + ")", "withheld_g3": wh})
            allr = pd.concat([res(1, "A", m), res(2, "B", m), res(3, "C", m)])
            wa = allr[allr.verdict == VR.WORSE]
            o, wh = g3(allr, any_worse, VR.WORSE)
            rules.append({"rule": "P2-R3", "measure": mn,
                          "outcome": (VR.NOT_TESTABLE_G3 if o is None else
                                      "clause not met on the measure: naive review can fall below automation" if o
                                      else "clause met on the measure: the hypothesis is refuted on the measure"),
                          "capacities_does_worse": "; ".join(f"team {r.team} at {r.capacity_label}" for r in wa.itertuples()),
                          "labels": " || ".join(f"team {r.team} at {r.capacity_label}: {r.labels}" for r in wa.itertuples()),
                          "capacity_1_flags": "; ".join(f"team {t_}" for t_, f_ in zip(allr.team, allr.get("capacity_1_overflow_flag", pd.Series([np.nan] * len(allr))))
                                                        if isinstance(f_, str) and f_), "withheld_g3": wh})
        else:
            allr = pd.concat([res(1, "A", m), res(2, "B", m), res(3, "C", m)])
            nb = allr[(allr.verdict != VR.BEATS) & (allr.verdict_route != "G3")]
            o, wh = g3(allr, lambda vs: any(v != VR.BEATS for v in vs), ("not", VR.BEATS))
            rules.append({"rule": "P3-R1", "measure": mn,
                          "outcome": VR.NOT_TESTABLE_G3 if o is None else ("clause met, hypothesis refuted on the measure" if o else "clause not met"),
                          "results_not_beats": "; ".join(f"team {r.team} at {r.capacity_label}: {r.verdict}" for r in nb.itertuples()),
                          "n_results": len(allr), "withheld_g3": wh})
            c46 = pd.concat([res(4, "A", m), res(5, "B", m), res(6, "C", m)])
            o, wh = g3(c46, lambda vs: all(v == VR.BEATS for v in vs), VR.BEATS)
            rules.append({"rule": "P3-R2", "measure": mn,
                          "outcome": VR.NOT_TESTABLE_G3 if o is None else ("supported on the measure" if o else "not supported on the measure"),
                          "verdicts": "; ".join(f"comparison {r.comparison} (team {r.team}, {r.capacity_label}): {r.verdict}"
                                                + (f" [{r.labels}]" if r.labels else "") for r in c46.itertuples()), "withheld_g3": wh})
    if P == 2:
        c5 = res(5, "C", "difference_expected_loss").iloc[0]
        word = {VR.WORSE: "costs", VR.BEATS: "saves", VR.NODIFF: "is not shown to differ in"}.get(c5.verdict, c5.verdict)
        rules.append({"rule": "P2-R4", "measure": "expected loss", "outcome": c5.verdict,
                      "statement": f"at 0.75 capacity, the bias rule {word} expected loss at 0.057 against the same reviewers without it",
                      "withheld_g3": ""})
    RULES = pd.DataFrame(rules)

    # ------------------------------------------------------------------ descriptive verdicts (P<k>-T5), P<k>-L, P<k>-U, P<k>-X
    d95 = iv[iv.level == "95%"].copy()
    d95["verdict"] = [VR.verdict(lo, hi) for lo, hi in zip(d95.ci_low, d95.ci_high)]
    is_diff = d95.comparison.isin(["vs_policy_1", "vs_policy_2", "vs_confirm_every_alert", "B_minus_A", "C_minus_A"])
    d95.loc[~is_diff & (d95.comparison != "bias_x_capacity"), "verdict"] = ""
    d95["deciding_note"] = ""
    # A cell carries the note if and only if its key (comparison, team, capacity, measure, cost ratio) is a deciding key,
    # at every version and at the mean. Policy 2 (P2-B (b)): the deciding keys of teams B and C against
    # policy 1 at the 9 realistic capacities, so expected loss only at 0.057. Policy 3 (P3-B): all 66.
    if P == 2:
        DKEYS = {(comp, t, cap, m, lam) for (k, comp, t, cap, m, lam) in spec if k in (2, 3)}
    else:
        DKEYS = {(comp, t, cap, m, lam) for (_, comp, t, cap, m, lam) in spec}
    mask = pd.Series([(r.comparison, r.team, r.capacity_label, r.measure, r["lambda"]) in DKEYS for _, r in d95.iterrows()], index=d95.index)
    d95.loc[mask, "deciding_note"] = f"deciding verdict: see P{P}-T3"
    sr = [per_seed(r.comparison, r.team, r.version, r.capacity_label, r.measure, r["lambda"]) if r.comparison in
          ("vs_policy_1", "vs_policy_2", "B_minus_A", "C_minus_A") else None for _, r in d95.iterrows()]
    d95["seed_min"] = [x[0] if x else np.nan for x in sr]
    d95["seed_max"] = [x[1] if x else np.nan for x in sr]
    d95["labels"] = ""
    if P == 2:     # age-gap property (section 6), on the vs-policy-1 age-gap results
        fr_idx = {(r.team, r.version, r.capacity_label): r.point_estimate for r in d95[(d95.comparison == "vs_policy_1") & (d95.measure == "difference_overall_false_rejection_rate")].itertuples()}
        for i, r in d95[(d95.comparison == "vs_policy_1") & (d95.measure == "difference_age_gap_abs")].iterrows():
            if VR.age_property_p2(r.point_estimate, fr_idx[(r.team, r.version, r.capacity_label)]):
                d95.at[i, "labels"] = VR.LBL_AGE_PROPERTY
    # P-L at 0.035
    lrows = d95[(d95.comparison == "vs_policy_1") & (d95.measure == "difference_expected_loss") & (d95["lambda"] == "0.035") & (d95.verdict == VR.BEATS)]
    for i, r in lrows.iterrows():
        ce = row("vs_confirm_every_alert", r.team, r.version, r.capacity_label, "difference_expected_loss", "0.035")
        if vword(ce) != VR.BEATS:
            d95.at[i, "labels"] = (d95.at[i, "labels"] + " | " if d95.at[i, "labels"] else "") + VR.LBL_P2L
    # P-U
    urows = []
    over = None if a.p2u_over == "all" else [l for l in LAMS if l != 0.057]
    el = d95[(d95.comparison == "vs_policy_1") & (d95.measure == "difference_expected_loss")]
    for (t, v, cap), g in el.groupby(["team", "version", "capacity_label"]):
        vb = {float(l): w for l, w in zip(g["lambda"], g.verdict)}
        lab_, b, w, breaks = VR.p2u_label(vb, over=over)
        urows.append({"team": t, "version": v, "capacity_label": cap, "label": lab_, "beats_at": ", ".join(map(str, b)),
                      "does_worse_at": ", ".join(map(str, w)), **{f"verdict_{l}": vb[l] for l in LAMS},
                      "break_even_notes": "; ".join(f"{l}: {VR.LBL_BREAK_EVEN} ({vb[0.057]} at 0.057, {vb[l]} at {l})" for l in breaks),
                      "qualifier": VR.LBL_P2U_QUALIFIER if any(vb[l] == VR.BEATS for l in LAMS if l != 0.057) else ""})
    UROWS = pd.DataFrame(urows)

    # ------------------------------------------------------------------ boundaries (P<k>-B (a), (b))
    MIXED_FORM_NOTE = ("mixed pattern: the summary lists every verdict, not the design's two-capacity form; the design form's two "
                       "capacities are in columns interval_highest_does_worse and interval_lowest_beats_from (review 20261019-0055, N4)")
    brows = []
    comps = ["vs_policy_1"] + (["vs_policy_2"] if P == 3 else [])
    for comp in comps:
        for t in TEAMS:
            for v in VERS + [MEAN]:
                for m, lam in DEC_MEASURES:
                    q = d95[(d95.comparison == comp) & (d95.team == t) & (d95.version == v) & (d95.measure == m) & (d95["lambda"] == lam)]
                    assert len(q) == 22, (comp, t, v, m, len(q))
                    pb = VR.point_boundary(list(zip(q.capacity_label, q.point_estimate)))
                    ib = VR.interval_boundary(list(zip(q.capacity_label, q.verdict)))
                    brows.append({"comparison": comp, "team": t, "version": v, "measure": m, "lambda": lam,
                                  "point_boundary": " ; ".join(it["text"] for it in pb),
                                  "point_boundary_capacities": json.dumps([it["capacity"] for it in pb if it["kind"].startswith("crossing")]),
                                  "interval_highest_does_worse": ib["highest_does_worse"], "interval_lowest_beats_from": ib["lowest_beats_from"],
                                  "interval_pattern": ib["pattern"], "interval_summary": ib["text"],
                                  "interval_summary_form": (MIXED_FORM_NOTE if ib["pattern"] == "mixed" else "design form (P%d-B (b))" % P),
                                  "verdicts_by_capacity": "; ".join(f"{c}: {w}" for c, w in sorted(zip(q.capacity_label, q.verdict), key=lambda x: VR.cap_value(x[0])))})
    BROWS = pd.DataFrame(brows)

    # ------------------------------------------------------------------ chance count (P<k>-N)
    cn = d95[(d95.comparison == "vs_policy_1") & d95.version.isin(VERS) &
             (((d95.measure == "difference_expected_loss")) | ((d95.measure.isin(["difference_accepted_frauds", "difference_age_gap_abs"])) & (d95["lambda"] == "")))]
    above0 = cn[cn.capacity_label != "0.00"]
    if P == 2:
        at0 = cn[(cn.capacity_label == "0.00") & (cn.team == "A") & (cn.version == "1")]
        counted = pd.concat([above0, at0])
        n_expect = 21 * 15 * 6 + 6
    else:
        counted = above0
        n_expect = 21 * 15 * 6
    assert len(counted) == n_expect, (len(counted), n_expect)
    CHANCE = pd.DataFrame([{"rule": f"P{P}-N", "n_intervals": len(counted), "n_beats": int((counted.verdict == VR.BEATS).sum()),
                            "n_does_worse": int((counted.verdict == VR.WORSE).sum()), "expected_each_side": VR.chance_expected(len(counted)),
                            "set_counted": ("each of the 15 team instances against policy 1, at every grid capacity above 0; expected loss at 4 cost "
                                            "ratios, accepted frauds and the age gap; " + ("capacity 0 once per measure and cost ratio"
                                            if P == 2 else "capacity 0 left out")),
                            "note": "the expected number assumes independent intervals; a guide, not a test"}])

    # ------------------------------------------------------------------ bias x capacity (section 9)
    bx = d95[d95.comparison == "bias_x_capacity"].copy()
    bx["reading"] = [VR.section9_reading(lo, hi) for lo, hi in zip(bx.ci_low, bx.ci_high)]
    bx["kind"] = ["check, by construction" if (P == 2 and "expected_loss" not in m) else "finding" for m in bx.measure]


    files = {}
    for name, df in (("deciding", DEC), ("rules", RULES), ("descriptive", d95), ("cost_ratio_labels", UROWS), ("boundaries", BROWS),
                     ("chance", CHANCE), ("bias_x_capacity", bx)):
        p = os.path.join(a.out, f"{pre}_verdict_{name}.csv")
        df.to_csv(p, index=False, float_format="%.17g")
        files[os.path.basename(p)] = C.sha256(p)
    C.write_record(a, {"step": a.step, "policy": P, "g3_dropped": G3, "g3_withheld": g3_withhold, "n_deciding": N_DEC,
                       "zero_threshold": VR.ZERO, "p2u_over": a.p2u_over, "outputs_sha256": files})


if __name__ == "__main__":
    main()

"""
Per-case vectors and per-resample measures for the policy 2 and policy 3 bootstraps.
Plan step 2.1 (Implement and run the sweep; run register). Designs: policy 2 version 0.4, sections 6 and 7;
policy 3 version 0.13, sections 6 and 7 (frozen at Gate 1).

Route M5: the per-case inputs are the integer seed sums of the replay exports (`n_seeds_reviewed`,
`sum_decision`, ...). They are resampled as integers and the seed-dependent sums are divided by 5 afterwards;
numerator and denominator are treated alike (both divided by 5); costs and differences are formed after the
summation. Sums that do not depend on the seed (policy 1, the label and age-group counts) are not divided.

A "side" is one team instance (team, version) at one capacity. Its per-case vectors are integer-valued; their
per-resample sums come from the sums engine (boot_core.resample_sums). Every measure function takes a dict of
per-resample sums (arrays of equal length; length 1 for the point estimate) and returns {name: (values, defined)}.
"""
import numpy as np

SEEDS = 5.0

# policy 2 and policy 3 share these seed-sum columns (their replay exports)
BASE_COLS = ("n_seeds_reviewed", "sum_decision", "sum_reviewed_decision", "sum_reviewed_disagreement",
             "sum_reviewed_deferred")
P3_COLS = BASE_COLS + ("sum_reviewed_twin_right_p1_wrong", "sum_reviewed_twin_wrong_p1_right", "sum_p2_decision",
                       "sum_p2_decision_on_p3_reviewed", "sum_p2_reviewed")

CONST_NAMES = ("lo", "ly", "fr", "p1fp", "p1fn", "p1fpo", "p1fpy")


def const_vectors(label, age50, p1):
    """Per-case vectors that do not depend on the seed (one case counted once)."""
    leg = (label == 0).astype(np.int64); fr = (label == 1).astype(np.int64)
    old = (age50 == 1).astype(np.int64); yng = 1 - old
    p1 = p1.astype(np.int64)
    return {"lo": leg * old, "ly": leg * yng, "fr": fr, "p1fp": leg * p1, "p1fn": fr * (1 - p1),
            "p1fpo": leg * old * p1, "p1fpy": leg * yng * p1}


def side_vectors(sums, label, age50, p1, policy):
    """Per-case seed-sum vectors of one side (team instance at one capacity). `sums` maps the export's columns to
    int64 arrays in ascending case_id order. Every vector is an integer count over seeds (0 to 5 per case)."""
    leg = (label == 0).astype(np.int64); fr = (label == 1).astype(np.int64)
    old = (age50 == 1).astype(np.int64); yng = 1 - old
    p1 = p1.astype(np.int64)
    R = sums["n_seeds_reviewed"].astype(np.int64); D = sums["sum_decision"].astype(np.int64)
    RD = sums["sum_reviewed_decision"].astype(np.int64)
    assert np.all((0 <= R) & (R <= 5) & (0 <= D) & (D <= 5) & (0 <= RD) & (RD <= R))
    v = {
        "fpo": leg * old * D, "fpy": leg * yng * D, "fn": fr * (5 - D),
        "rev": R, "racc": R - RD, "rdif": np.where(p1 == 1, R - RD, RD),
        "rfp": leg * RD, "rfn": fr * (R - RD), "rp1fp": leg * p1 * R, "rp1fn": fr * (1 - p1) * R,
        "rlo": leg * old * R, "rly": leg * yng * R, "rfpo": leg * old * RD, "rfpy": leg * yng * RD,
        "dis": sums["sum_reviewed_disagreement"].astype(np.int64), "dfr": sums["sum_reviewed_deferred"].astype(np.int64),
    }
    if policy == 3:
        D2 = sums["sum_p2_decision"].astype(np.int64); D2r = sums["sum_p2_decision_on_p3_reviewed"].astype(np.int64)
        assert np.all((0 <= D2) & (D2 <= 5) & (0 <= D2r) & (D2r <= R) & (D2r <= D2) & (D2 - D2r <= 5 - R))
        U = 5 - R
        v.update({
            "crw": sums["sum_reviewed_twin_right_p1_wrong"].astype(np.int64),
            "cwr": sums["sum_reviewed_twin_wrong_p1_right"].astype(np.int64),
            "qfpo": leg * old * D2, "qfpy": leg * yng * D2, "qfn": fr * (5 - D2),
            # split against policy 2 (policy 3 design section 6; Plain terms "Split against policy 2, by seed")
            "c3fp": leg * p1 * U, "c3fn": fr * (1 - p1) * U,
            "c2fp": leg * (D2 - D2r), "c2fn": fr * (U - (D2 - D2r)),
            "r2fp": leg * D2r, "r2fn": fr * (R - D2r),
        })
    return v


def _div(a, b):
    with np.errstate(invalid="ignore", divide="ignore"):
        return a / b


def levels(s, c, lams, K, policy):
    """The measures of one side (policy 2 design section 6; policy 3 design section 6). Seed-dependent sums are
    divided by 5; ratios divide numerator and denominator alike."""
    n = len(s["fn"])
    one = np.ones(n, dtype=bool)
    FPo, FPy, FN = s["fpo"] / SEEDS, s["fpy"] / SEEDS, s["fn"] / SEEDS
    FP = FPo + FPy
    Lo, Ly, F = c["lo"], c["ly"], c["fr"]
    g3 = (Lo > 0) & (Ly > 0)                                    # G3: shared by both sides of any comparison
    fpr_o, fpr_y = _div(FPo, Lo), _div(FPy, Ly)
    out = {}
    for lam in lams:
        out[("expected_loss_total", lam)] = (lam * FP + FN, one)
    out[("regulatory_exposure_accepted_frauds_count", None)] = (FN, one)
    out[("regulatory_exposure_miss_rate", None)] = (_div(FN, F), F > 0)
    out[("fairness_exposure_age_gap_signed", None)] = (fpr_o - fpr_y, g3)
    out[("fairness_exposure_age_gap_abs", None)] = (np.abs(fpr_o - fpr_y), g3)
    out[("false_positive_rate_50_plus", None)] = (fpr_o, Lo > 0)
    out[("false_positive_rate_under_50", None)] = (fpr_y, Ly > 0)
    out[("overall_false_rejection_rate", None)] = (_div(FP, Lo + Ly), (Lo + Ly) > 0)
    out[("false_rejections_50_plus_count", None)] = (FPo, one)
    if K > 0:
        rev = s["rev"] / SEEDS
        okr = s["rev"] > 0
        out[("override_rate_accepted", None)] = (_div(s["racc"] / SEEDS, rev), okr)
        out[("override_rate_differs_from_classifier", None)] = (_div(s["rdif"] / SEEDS, rev), okr)
        team_cost = {lam: lam * s["rfp"] / SEEDS + s["rfn"] / SEEDS for lam in lams}
        for lam in lams:
            p1_cost = lam * s["rp1fp"] / SEEDS + s["rp1fn"] / SEEDS
            rej_cost = lam * (s["rlo"] + s["rly"]) / SEEDS
            out[("loss_avoided_per_review_vs_policy_1", lam)] = (_div(p1_cost - team_cost[lam], rev), okr)
            out[("loss_avoided_per_review_vs_rejection", lam)] = (_div(rej_cost - team_cost[lam], rev), okr)
        oks = (s["rlo"] > 0) & (s["rly"] > 0)
        out[("subgroup_disparity_reviewed", None)] = (
            _div(s["rfpo"] / SEEDS, s["rlo"] / SEEDS) - _div(s["rfpy"] / SEEDS, s["rly"] / SEEDS), oks)
        out[("team_b_share_disagreements_deferred", None)] = (_div(s["dfr"] / SEEDS, s["dis"] / SEEDS), s["dis"] > 0)
        if policy == 3:
            out[("load", None)] = (rev / K, one)
            out[("criterion_1_share_expert_right_policy_1_wrong", None)] = (_div(s["crw"] / SEEDS, rev), okr)
            out[("criterion_1_share_expert_wrong_policy_1_right", None)] = (_div(s["cwr"] / SEEDS, rev), okr)
    return out


def policy_1_levels(c, lams):
    """Policy 1's measures on the same resamples (not seed-dependent, not divided)."""
    n = len(c["fr"]); one = np.ones(n, dtype=bool)
    g3 = (c["lo"] > 0) & (c["ly"] > 0)
    gap = _div(c["p1fpo"], c["lo"]) - _div(c["p1fpy"], c["ly"])
    out = {("expected_loss_total", lam): (lam * c["p1fp"] + c["p1fn"], one) for lam in lams}
    out[("regulatory_exposure_accepted_frauds_count", None)] = (c["p1fn"].astype(float), one)
    out[("fairness_exposure_age_gap_signed", None)] = (gap, g3)
    out[("fairness_exposure_age_gap_abs", None)] = (np.abs(gap), g3)
    out[("overall_false_rejection_rate", None)] = (_div(c["p1fp"], c["lo"] + c["ly"]), (c["lo"] + c["ly"]) > 0)
    out[("false_rejections_50_plus_count", None)] = (c["p1fpo"].astype(float), one)
    return out


def side_policy_2_levels(s, c, lams):
    """Policy 3 runs only: policy 2's measures at the same team, version and capacity (its seed sums)."""
    n = len(s["qfn"]); one = np.ones(n, dtype=bool)
    FPo, FPy, FN = s["qfpo"] / SEEDS, s["qfpy"] / SEEDS, s["qfn"] / SEEDS
    g3 = (c["lo"] > 0) & (c["ly"] > 0)
    gap = _div(FPo, c["lo"]) - _div(FPy, c["ly"])
    out = {("expected_loss_total", lam): (lam * (FPo + FPy) + FN, one) for lam in lams}
    out[("regulatory_exposure_accepted_frauds_count", None)] = (FN, one)
    out[("fairness_exposure_age_gap_signed", None)] = (gap, g3)
    out[("fairness_exposure_age_gap_abs", None)] = (np.abs(gap), g3)
    out[("overall_false_rejection_rate", None)] = (_div(FPo + FPy, c["lo"] + c["ly"]), (c["lo"] + c["ly"]) > 0)
    out[("false_rejections_50_plus_count", None)] = (FPo, one)
    return out


def difference(a, b, lams):
    """First named minus second named, on the same resamples; the age gap as |gap| of the first minus |gap| of
    the second (policy 2 design section 7). Defined where both sides are."""
    out = {}
    for lam in lams:
        x, ox = a[("expected_loss_total", lam)]; y, oy = b[("expected_loss_total", lam)]
        out[("difference_expected_loss", lam)] = (x - y, ox & oy)
    for m_in, m_out in (("regulatory_exposure_accepted_frauds_count", "difference_accepted_frauds"),
                        ("fairness_exposure_age_gap_abs", "difference_age_gap_abs"),
                        ("fairness_exposure_age_gap_signed", "difference_age_gap_signed"),
                        ("overall_false_rejection_rate", "difference_overall_false_rejection_rate"),
                        ("false_rejections_50_plus_count", "difference_false_rejections_50_plus")):
        x, ox = a[(m_in, None)]; y, oy = b[(m_in, None)]
        out[(m_out, None)] = (x - y, ox & oy)
    return out


def split_policy_2_vs_policy_1(s, c, lams):
    """Policy 2 design section 6: reviewed-cases part and unreviewed-cases part of (policy 2 - policy 1), for
    expected loss and accepted frauds; integer sums formed first, divided by 5 once."""
    n = len(s["fn"]); one = np.ones(n, dtype=bool)
    FP5 = s["fpo"] + s["fpy"]
    ufp = FP5 - s["rfp"]                         # unreviewed seeds: every legitimate alert rejected
    up1fp = SEEDS * c["p1fp"] - s["rp1fp"]
    up1fn = SEEDS * c["p1fn"] - s["rp1fn"]
    out = {}
    for lam in lams:
        out[("reviewed_part_expected_loss", lam)] = (((lam * s["rfp"] + s["rfn"]) - (lam * s["rp1fp"] + s["rp1fn"])) / SEEDS, one)
        out[("unreviewed_part_expected_loss", lam)] = ((lam * (ufp - up1fp) - up1fn) / SEEDS, one)
    out[("reviewed_part_accepted_frauds", None)] = ((s["rfn"] - s["rp1fn"]) / SEEDS, one)
    out[("unreviewed_part_accepted_frauds", None)] = ((0 - up1fn) / SEEDS, one)
    return out


def split_policy_3_vs_policy_2(s, lams):
    """Policy 3 design section 6: classifier part and reviewed part of (policy 3 - policy 2)."""
    n = len(s["fn"]); one = np.ones(n, dtype=bool)
    out = {}
    for lam in lams:
        out[("classifier_part_expected_loss", lam)] = (((lam * s["c3fp"] + s["c3fn"]) - (lam * s["c2fp"] + s["c2fn"])) / SEEDS, one)
        out[("reviewed_part_expected_loss", lam)] = (((lam * s["rfp"] + s["rfn"]) - (lam * s["r2fp"] + s["r2fn"])) / SEEDS, one)
    out[("classifier_part_accepted_frauds", None)] = ((s["c3fn"] - s["c2fn"]) / SEEDS, one)
    out[("reviewed_part_accepted_frauds", None)] = ((s["rfn"] - s["r2fn"]) / SEEDS, one)
    return out


def confirm_every_alert_levels(c, lams):
    n = len(c["fr"]); one = np.ones(n, dtype=bool)
    return {("expected_loss_total", lam): (lam * (c["lo"] + c["ly"]).astype(float), one) for lam in lams}


def mean_of_five(per_version):
    """The mean of the five versions' values, per resample; defined where all five are."""
    keys = per_version[0].keys()
    out = {}
    for k in keys:
        xs = [pv[k][0] for pv in per_version]
        oks = [pv[k][1] for pv in per_version]
        out[k] = (sum(xs) / 5.0, np.logical_and.reduce(oks))
    return out

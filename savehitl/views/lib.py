"""Shared constants and helpers of the notebook's tables and graphs (run in the pinned environment by the step `views`).

Ported from the study's results-notebook helpers. It reads the run's own outputs only: `csv(key)` and `js(key)` resolve
a key to a file written by an earlier step of this run (KEYS), and check the file against the sha256 that step
recorded in its `record.json`; the check is written to the run's own assertion log and stops on a difference. Nothing
here computes an interval, a verdict or a rule outcome: those are read as the steps wrote them. Point figures formed
here (means over seeds and versions, shares from counts) are labelled "formed once, in this notebook".

Label texts: the study's texts, with the sentences that cite the study's own registered runs and checks left out (the
re-run has no registered checks and states no run number).
"""
import hashlib
import json
import os

import numpy as np
import pandas as pd

ROOT = None          # the repository root, set by init()
OUT_TABLES = None
OUT_FIGURES = None
_ASSERT = None       # the step's assertion object (steps._common.Asserts), set by init()

# key -> (step folder under outputs/, file). The policy 2 and policy 3 verdict tables are written by the steps
# verdicts2 and verdicts3; the summaries step forms P2-T1 and P3-T9 and the router's ranking summary.
KEYS = {
    "p1_t2_intervals": ("policy1_intervals", "p1_t2_measures_by_lambda_with_intervals.csv"),
    "p2_cells": ("policy2", "p2_cell_measures.csv"),
    "p2_desc": ("verdicts2", "p2_verdict_descriptive.csv"),
    "p2_dec": ("verdicts2", "p2_verdict_deciding.csv"),
    "p2_rules": ("verdicts2", "p2_verdict_rules.csv"),
    "p2_bound": ("verdicts2", "p2_verdict_boundaries.csv"),
    "p2_chance": ("verdicts2", "p2_verdict_chance.csv"),
    "p2_costlab": ("verdicts2", "p2_verdict_cost_ratio_labels.csv"),
    "p2_bxc": ("verdicts2", "p2_verdict_bias_x_capacity.csv"),
    "p3_cells": ("policy3", "p3_cell_measures.csv"),
    "p3_routing": ("policy3", "p3_routing_summary.csv"),
    "p3_access": ("policy3", "p3_access_by_age.csv"),
    "p3_t8": ("policy3", "p3_t8_point_figures.csv"),
    "p3_desc": ("verdicts3", "p3_verdict_descriptive.csv"),
    "p3_dec": ("verdicts3", "p3_verdict_deciding.csv"),
    "p3_rules": ("verdicts3", "p3_verdict_rules.csv"),
    "p3_bound": ("verdicts3", "p3_verdict_boundaries.csv"),
    "p3_chance": ("verdicts3", "p3_verdict_chance.csv"),
    "p3_costlab": ("verdicts3", "p3_verdict_cost_ratio_labels.csv"),
    "p3_bxc": ("verdicts3", "p3_verdict_bias_x_capacity.csv"),
    "p3_rank_model": ("ranking", "p3_ranking_month7_per_model.csv"),
    "p3_rank_version": ("ranking", "p3_ranking_month7_by_version.csv"),
    "p3_rank_month6_model": ("ranking", "p3_ranking_month6_per_model.csv"),
    "s_members": ("summaries", "P2-T1a_members_slot_order.csv"),
    "s_draw": ("summaries", "P2-T1b_draw.csv"),
    "s_version_rates": ("summaries", "P2-T1c_team_version_rates.csv"),
    "s_twins": ("summaries", "P2-T1d_twins.csv"),
    "s_month7_items": ("summaries", "P2-T1e_month7_items.csv"),
    "s_access_by_age": ("summaries", "P3-T9_access_by_age.csv"),
    "s_access_per_seed": ("summaries", "P3-T9a_per_seed.csv"),
    "s_ranking": ("summaries", "P3-T1_ranking_month6_month7.csv"),
    # aggregate figures of the applications (step applications) and descriptive figures (step descriptive)
    "a_month": ("applications", "applications_by_month.csv"),
    "a_age": ("applications", "applications_by_age.csv"),
    "a_month_age": ("applications", "applications_by_month_age.csv"),
    "a_spearman": ("applications", "applications_spearman.csv"),
    "a_columns": ("applications", "applications_columns.csv"),
    "a_flag": ("applications", "alert_model_flag_by_age.csv"),
    "a_test_month": ("applications", "test_month_by_age.csv"),
    "d_fpfn": ("descriptive", "fpr_fnr_by_age_075.csv"),
    "d_reviewers": ("descriptive", "reviewers_month7.csv"),
    "d_roc": ("descriptive", "classifier_roc_month7.csv"),
    "d_point": ("descriptive", "classifier_point_month7.csv"),
}
MIN_GROUP = 10       # no figure over applications from fewer than 10 (the aggregate figures' safeguard)
_CHECKED = set()


def init(root, asserts):
    global ROOT, OUT_TABLES, OUT_FIGURES, _ASSERT
    ROOT = root
    OUT_TABLES = os.path.join(root, "tables")
    OUT_FIGURES = os.path.join(root, "figures")
    os.makedirs(OUT_TABLES, exist_ok=True)
    os.makedirs(OUT_FIGURES, exist_ok=True)
    _ASSERT = asserts


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def path(key):
    step, name = KEYS[key]
    p = os.path.join(ROOT, "outputs", step, name)
    if key not in _CHECKED:
        rec = json.load(open(os.path.join(ROOT, "outputs", step, "record.json")))
        want = (rec.get("outputs_sha256") or {}).get(name)
        _ASSERT.check(want is not None and _sha256(p) == want, "view input equal to the checksum its step recorded",
                      key=key, step=step, file=name)
        _CHECKED.add(key)
    return p


def csv(key, **kw):
    return pd.read_csv(path(key), **kw)


def record(step):
    """A step's own record.json (read, not checked: it holds the checksums the inputs are checked against)."""
    return json.load(open(os.path.join(ROOT, "outputs", step, "record.json")))


# ------------------------------------------------------------------ capacities, teams, names
CAP_ORDER = ["0.00", "0.05", "0.10", "0.15", "0.20", "0.25", "0.30", "0.35", "0.40", "0.45", "0.50", "0.55", "0.60", "0.65",
             "0.70", "0.75", "0.80", "0.85", "0.90", "10/11", "0.95", "1.00"]
assert len(CAP_ORDER) == 22
REALISTIC = ["0.65", "0.70", "0.75", "0.80", "0.85", "0.90", "10/11", "0.95", "1.00"]
T_CAPS = ["1.00", "10/11", "0.75", "0.65"]                  # P3-T1, P3-T9


def cap_value(label):
    s = str(label)
    if s == "10/11":
        return 10 / 11
    return float(s)


def cap_label(x):
    """Normalise a capacity label read as text or number to the export's text form."""
    s = str(x).strip()
    if s in ("10/11", "0.9090909090909091"):
        return "10/11"
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return s


VERSIONS = ["1", "2", "3", "4", "5"]
MEAN5 = "mean of 5 versions"
TEAMS = ["A", "B", "C"]

MEASURE_NAMES = {
    "difference_expected_loss": "expected loss, difference",
    "difference_accepted_frauds": "regulatory exposure (accepted frauds), difference",
    "difference_age_gap_abs": "fairness exposure (absolute age gap), difference",
    "difference_age_gap_signed": "fairness exposure (signed age gap), difference",
    "difference_false_rejections_50_plus": "false rejections aged 50 or over, difference",
    "difference_overall_false_rejection_rate": "overall false rejection rate, difference",
    "reviewed_part_expected_loss": "expected loss, reviewed-cases part",
    "unreviewed_part_expected_loss": "expected loss, unreviewed-cases part",
    "reviewed_part_accepted_frauds": "regulatory exposure (accepted frauds), reviewed-cases part",
    "unreviewed_part_accepted_frauds": "regulatory exposure (accepted frauds), unreviewed-cases part",
    "classifier_part_expected_loss": "expected loss, classifier part",
    "classifier_part_accepted_frauds": "regulatory exposure (accepted frauds), classifier part",
    "expected_loss_total": "expected loss (total)",
    "expected_loss_per_case": "expected loss (per case)",
    "regulatory_exposure_accepted_frauds_count": "regulatory exposure (accepted frauds)",
    "regulatory_exposure_miss_rate": "regulatory exposure (miss rate)",
    "regulatory_exposure_share_stopped": "regulatory exposure (share of frauds stopped)",
    "fairness_exposure_age_gap": "fairness exposure (age gap)",
    "fairness_exposure_age_gap_abs": "fairness exposure (absolute age gap)",
    "fairness_exposure_age_gap_signed": "fairness exposure (signed age gap)",
    "false_positive_rate_50_plus": "false rejection rate, aged 50 or over",
    "false_positive_rate_under_50": "false rejection rate, under 50",
    "false_rejections_count": "false rejections (count)",
    "false_rejections_50_plus_count": "false rejections aged 50 or over (count)",
    "overall_false_rejection_rate": "overall false rejection rate",
    "override_rate_accepted": "override rate (share of reviewed alerts accepted)",
    "override_rate_differs_from_classifier": "share of reviewed alerts decided differently from the classifier",
    "loss_avoided_per_review_vs_policy_1": "loss avoided per review, against policy 1",
    "loss_avoided_per_review_vs_rejection": "loss avoided per review, against confirming every alert",
    "subgroup_disparity_reviewed": "subgroup disparity on reviewed alerts",
    "team_b_share_disagreements_deferred": "team B: share of disagreements deferred",
    "load": "load (alerts reviewed / K)",
    "criterion_1_share_expert_right_policy_1_wrong": "criterion 1: share expert right, policy 1 wrong",
    "criterion_1_share_expert_wrong_policy_1_right": "criterion 1: share expert wrong, policy 1 right",
    "bias_x_capacity_I_expected_loss_total_0.057": "expected loss at 0.057",
    "bias_x_capacity_I_fairness_exposure_age_gap_signed": "fairness exposure (signed age gap)",
    "bias_x_capacity_I_false_rejections_50_plus_count": "false rejections aged 50 or over (count)",
}


def mname(m):
    return MEASURE_NAMES.get(m, m)


COMPARISON_NAMES = {"vs_policy_1": "against policy 1", "vs_policy_2": "against policy 2", "B_minus_A": "team B minus team A",
                    "C_minus_A": "team C minus team A", "vs_confirm_every_alert": "against confirming every alert",
                    "level": "level", "policy_2_side": "policy 2 side", "bias_x_capacity": "bias × capacity"}

# ------------------------------------------------------------------ labels (exact wording: analyst's note 20261019-0850, section 3)
L_P1 = "95% case-bootstrap interval, B = 1,000 (rows 0 to 999 of the shared index matrix)."
L_P2_DEC = ("Deciding result, one of 61. Interval adjusted for 61 results (1 − 0.05/61, about 99.918%; ends at the 0.0410th and "
            "99.9590th percentiles), B = 50,000. Verdict by the five-version rule.")
L_P2K = "Fixed by construction (P2-K); not a finding."
L_P3_DEC = ("Deciding result, one of 66. Interval adjusted for 66 results (1 − 0.05/66, about 99.924%; ends at the 0.0379th and "
            "99.9621st percentiles), B = 50,000. Verdict by the five-version rule. Adjusted among policy 3's "
            "66 only, not together with policy 2's 61.")
L_DESC = ("Descriptive: 95% interval, B = 50,000; verdict from the mean of the five versions at 95%. Not a deciding result; may "
          "differ from a deciding verdict on the same measure.")
L_RULE = ("Rule outcome. The boundary summaries and statement sentences beside it were formed once "
          "by the verdict script and not recomputed.")
L_P3_VS_P2_OTHER = "Descriptive"
L_POINT_FORMED_HERE = ("Point figure; no interval and no verdict. Formed once, in this notebook, from the registered export named "
                       "with the table, with no second route.")
# L_T8 and L_AA: exact wording of the analyst's note 20261019-1410, sections 2 and 1
L_T8 = ("Point figure; no interval and no verdict (policy 3 design section 8.2). Per-seed figures and their means as exported "
        "by the policy 3 step (`p3_t8_point_figures.csv`), not recomputed in this notebook. The seed lowest and highest (the lowest "
        "and highest of the five seeds' figures in a version) were formed once, in this notebook, from the per-seed rows, with no "
        "second route.")
L_AA = ("Point figure; no interval and no verdict. Formed once, in this notebook, from the counts of the four groups (age group by "
        "the classifier's decision), with no second route: the overall counts behind share (i); the counts summed over seeds and "
        "versions; the shares; their seed lowest and highest (the lowest and highest of the five seeds' shares in a version); their "
        "means over seeds and versions; and the differences between the age groups.")

# P3-T9 labels: policy 3 design section 10, row P3-T9 (line 541), exact text
T9_C_ZERO = "0 by construction"
T9_B_EQUAL = "identical to team A by construction"
T9_P2_C_CELL = ("Reviewed, but the outcome is fixed by team C's rule: every such alert is confirmed under policies 1, 2 and 3 "
                "(policy 2 and policy 3 designs, section 2.1). The share is review capacity spent without effect on the decision: "
                "access to a reviewer, not a better outcome.")
T9_ROW_I_NOTE = "Policy 2's overall share for applicants aged 50 or over includes these alerts."
T9_NOT_DEFINED = "Not defined"
# P3-F9 labels: policy 3 design section 10, row P3-F9 (line 542), exact text
F9_C_ZERO = "0 by construction"
F9_P2_C = "naive review, 50 or over: reviewed, but team C's rule fixes the outcome; the alert is confirmed under every policy"   # S2-D-444 (1), L8
F9_B_EQUAL = "identical to team A by construction"
F9_NOTE = "Policy 2's dashed lines are the same in every panel."




# ------------------------------------------------------------------ table helpers
def save(df, name, index=False):
    df.to_csv(os.path.join(OUT_TABLES, name), index=index)


def savefig(fig, name):
    retext_figure(fig)
    fig.savefig(os.path.join(OUT_FIGURES, name), dpi=110, bbox_inches="tight")


# ------------------------------------------------------------------ display terminology (notebook display only)
# The notebook displays "misclassification cost" for the study's "expected loss", FPR for "false rejection rate", FNR for
# "miss rate" and FP for a count of false rejections. Applied to what is displayed only (graph texts and the headers and
# texts of displayed tables); the files in `tables/` and every step output keep the study's internal names.
DISPLAY_TERMS = [
    ("expected loss at 0.057", "misclassification cost"),   # S2-D-476: 0.057 is the default and is not repeated (display only)
    ("expected-loss difference", "misclassification-cost difference"), ("Expected-loss", "Misclassification-cost"),
    ("expected-loss", "misclassification-cost"), ("Expected loss", "Misclassification cost"), ("expected loss", "misclassification cost"),
    ("Loss avoided per review", "Cost avoided per review"), ("loss avoided per review", "cost avoided per review"),
    ("overall false rejection rates", "overall FPRs"), ("overall false rejection rate", "overall FPR"),
    ("false rejection rate of legitimate applicants aged 50 or over", "FPR₅₀₊"),
    ("false rejection rate of legitimate applicants under 50", "FPR<₅₀"),
    ("false rejection rate, aged 50 or over", "FPR₅₀₊"), ("false rejection rate, under 50", "FPR<₅₀"),
    ("False rejection rates", "FPRs"), ("false rejection rates", "FPRs"), ("False rejection rate", "FPR"), ("false rejection rate", "FPR"),
    ("false rejections aged 50 or over", "FP among applicants aged 50 or over"), ("false rejections of legitimate applicants aged 50 or over",
     "FP among applicants aged 50 or over"), ("False rejections", "FP"), ("false rejections", "FP"),
    ("regulatory exposure (miss rate)", "regulatory exposure (FNR)"), ("miss rate", "FNR"),
]


def display_text(s):
    if not isinstance(s, str):
        return s
    for a, b in DISPLAY_TERMS:
        s = s.replace(a, b)
    return s


def retext_figure(fig):
    """Applies the display terminology to every text of a figure (titles, axis labels, ticks, legends, annotations)."""
    import matplotlib.text as mtext
    for t in fig.findobj(mtext.Text):
        old = t.get_text()
        new = display_text(old)
        if new != old:
            t.set_text(new)


AGE_GAP_FORMULA = {   # [analyst-18]: the size of the age gap as the difference of the two policies' sizes, policies as subscripts
    "naive-auto": r"$|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{\mathrm{naive}}-|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{\mathrm{auto}}$",
    "deferral-auto": r"$|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{\mathrm{deferral}}-|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{\mathrm{auto}}$",
    "deferral-naive": r"$|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{\mathrm{deferral}}-|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{\mathrm{naive}}$",
    "B-A": r"$|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{B}-|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{A}$",
    "C-A": r"$|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{C}-|\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50}|_{A}$",
    "signed C-A": r"$(\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50})_{C}-(\mathrm{FPR}_{50+}-\mathrm{FPR}_{<50})_{A}$",
}
FPR_DEFINITION = ("FPR among the alerts: the share of legitimate applicants in the alerts whose application is rejected (wrongly "
                  "rejected ÷ all legitimate), in the age group shown (50 or over; under 50). |…| is the size of the gap. Below zero: "
                  "the first policy's gap is closer to zero.")
FPR_REMINDER = "FPR among the alerts."


def fmt(x, nd=4):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v == int(v) and abs(v) < 1e12:
        return f"{int(v):,}"
    return f"{v:.{nd}g}" if abs(v) < 1e-3 else f"{v:,.{nd}f}"


def desc_load(key):
    d = csv(key, dtype={"version": str, "capacity_label": str, "lambda": str})
    d["capacity_label"] = d["capacity_label"].map(lambda s: s if " vs " in str(s) else cap_label(s))
    for c in ("point_estimate", "ci_low", "ci_high", "seed_min", "seed_max"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["cap"] = d["capacity_label"].map(lambda s: np.nan if " vs " in str(s) else cap_value(s))
    return d


def lam_eq(series, lam):
    return pd.to_numeric(series, errors="coerce").sub(lam).abs() < 1e-12


# ------------------------------------------------------------------ verdict symbols (used in every table with a verdict column)
SYMBOLS = {"beats": "✅", "does worse": "❌", "no difference shown": "🟡"}


def symbol(text, deciding=False):
    """The verdict text as its symbol; with `deciding`, the symbol of a cell that is also a deciding result (✅*, ❌*, 🟡*).
    A text that is not a verdict is returned unchanged; an empty cell stays empty."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return text
    s = str(text).strip()
    for v, mark in SYMBOLS.items():
        if s == v:
            return mark + ("*" if deciding else "")
        if s.startswith(v + " (deciding verdict"):
            return mark + "*"
    return text


def symbols(series, deciding=False):
    return [symbol(x, deciding) for x in series]

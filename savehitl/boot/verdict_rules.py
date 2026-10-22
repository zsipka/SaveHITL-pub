"""
Verdict rules shared by the policy 2 and policy 3 verdict scripts. Plan step 2.1 (Implement and run the sweep; run
register). Designs (frozen at Gate 1): policy 2 version 0.4, sections 6, 7, 8.2, 8.3, 9; policy 3 version
0.13, sections 6, 7, 8.2, 8.3, 9. The verdict words are computed from the exported interval ends only; the point
boundary from the exported point estimates only. Checks P2-V and P3-V recompute these by a separate route
(src/bootstrap/pv_check.py), which does not import this module.
"""
import math

ZERO = 1e-9
WORSE, BEATS, NODIFF = "does worse", "beats", "no difference shown"
NOT_GIVEN_G3 = "not given (G3: more than 500 resamples dropped; escalated)"
NOT_TESTABLE_G3 = "not testable (G3; escalated)"
G3_LIMIT = 500

LBL_REVIEWERS = "the reviewers themselves do worse than policy 1 on the alerts they review"
LBL_OVERFLOW = ("consequence of the overflow rule: overload makes naive review worse because the alerts beyond "
                "capacity are rejected unreviewed")
LBL_BOTH = ("consequence of the overflow rule; worse through both parts together; neither part is above 0 on its own")
LBL_COMP4 = "direction set by team A's difference on reviewed cases"
LBL_AGE_P2R2 = "age gap: cause not split; read with the age-gap property of section 6"
LBL_AGE_PROPERTY = "gap narrowed by rejecting more applicants in both groups"
LBL_BY_CONSTRUCTION = "by construction"
LBL_P2L = "beats policy 1, but not the cheaper automated option at this cost ratio"
LBL_P2U_QUALIFIER = "against an automation baseline not re-optimised for this cost ratio"
LBL_BREAK_EVEN = "the break-even lies between 0.057 and the tested ratio"


def z(x):
    """An endpoint with absolute value at most 1e-9 is treated as 0 (policy 2 design section 7)."""
    return 0.0 if abs(x) <= ZERO else x


def verdict(lo, hi):
    if lo is None or hi is None or (isinstance(lo, float) and math.isnan(lo)) or (isinstance(hi, float) and math.isnan(hi)):
        return "not defined"
    if z(lo) > 0:
        return WORSE
    if z(hi) < 0:
        return BEATS
    return NODIFF


def age_property_p2(abs_gap_diff, frr_diff):
    """Policy 2's age-gap property label (policy 2 design section 6): policy 2 minus policy 1, on point
    estimates, absolute-gap difference below 0 and overall false-rejection-rate difference above 0. A point
    difference within 1e-9 counts as 0."""
    return z(abs_gap_diff) < 0 and z(frr_diff) > 0


def age_property_p2_side(p3_minus_p2_abs_gap, p3_minus_p2_frr):
    """Policy 3, comparisons 5 and 6 only, mean of the five versions only (policy 3 design section 6):
    the label on the policy 2 side. Differences are policy 3 minus policy 2, so the signs are reversed:
    absolute-gap difference above 0 (policy 2 closer to zero) and false-rejection-rate difference below 0 (policy 2
    higher). A point difference within 1e-9 counts as 0."""
    return z(p3_minus_p2_abs_gap) > 0 and z(p3_minus_p2_frr) < 0


def above_zero(lo):
    """A part is 'above 0' when its 95% interval lies entirely above 0 (policy 2 design 8.3, P2-R1)."""
    return z(lo) > 0


def five_version_outcome(version_verdicts, mean_verdict):
    """Policy 2 design section 7: does worse if all five versions do worse; beats if all five beat; otherwise the
    verdict of the mean of the five versions. Returns (outcome, route)."""
    assert len(version_verdicts) == 5
    if all(v == WORSE for v in version_verdicts):
        return WORSE, "all five versions"
    if all(v == BEATS for v in version_verdicts):
        return BEATS, "all five versions"
    return mean_verdict, "mean of the five versions"


def g3_two_completions(holds, verdicts, withheld, trigger):
    """A rule outcome when G3 withholds some verdicts (analyst's note 20261019-0101, 1.6).
    holds(verdicts) -> bool is the rule as written. The rule is evaluated twice: once with every withheld verdict set
    to the word that triggers the rule, once with none of them set to it. trigger is the triggering word, or
    ("not", w) for a rule triggered by any word other than w. Returns (holds_value or None, withheld_count): None
    where the two completions differ, so the outcome on the measure is NOT_TESTABLE_G3."""
    assert len(verdicts) == len(withheld)
    if isinstance(trigger, tuple):
        on, off = "withheld, set to a word other than " + trigger[1], trigger[1]
    else:
        on, off = trigger, "withheld, set to a word other than " + trigger
    with_t = holds([on if w else v for v, w in zip(verdicts, withheld)])
    without = holds([off if w else v for v, w in zip(verdicts, withheld)])
    return (with_t if with_t == without else None), int(sum(bool(w) for w in withheld))


def split_label(rev_lo95, unrev_lo95):
    """P2-R1 / P2-R3 label of a 'does worse' on expected loss or accepted frauds, from the 95% lower ends of the
    two parts of the mean of the five versions."""
    if above_zero(rev_lo95):
        return LBL_REVIEWERS
    if above_zero(unrev_lo95):
        return LBL_OVERFLOW
    return LBL_BOTH


def cap_value(label):
    return 10 / 11 if label == "10/11" else float(label)


def point_boundary(series):
    """P2-B (a). series: [(capacity_label, point difference)] over the grid, any order. Returns a list of items,
    each {kind, capacity or interval, text}: kind in crossing, crossing_at, crossing_run, touches, none."""
    s = sorted(series, key=lambda t: cap_value(t[0]))
    caps = [cap_value(c) for c, _ in s]
    labs = [c for c, _ in s]
    d = [z(x) for _, x in s]
    items = []
    n = len(d)
    i = 0
    while i < n:
        if d[i] == 0:
            j = i
            while j + 1 < n and d[j + 1] == 0:
                j += 1
            left = next((d[k] for k in range(i - 1, -1, -1) if d[k] != 0), None)
            right = next((d[k] for k in range(j + 1, n) if d[k] != 0), None)
            opposite = left is not None and right is not None and (left > 0) != (right > 0)
            if opposite and i == j:
                items.append({"kind": "crossing_at", "capacity": caps[i], "text": f"crossing at capacity {labs[i]}"})
            elif opposite:
                items.append({"kind": "crossing_run", "capacity": (caps[i], caps[j]),
                              "text": f"between capacity {labs[i]} and {labs[j]}, at zero throughout"})
            elif i == j:
                items.append({"kind": "touches", "capacity": caps[i], "text": f"touches zero at capacity {labs[i]}"})
            else:
                items.append({"kind": "touches", "capacity": (caps[i], caps[j]),
                              "text": f"touches zero from capacity {labs[i]} to {labs[j]}"})
            i = j + 1
            continue
        if i + 1 < n and d[i + 1] != 0 and (d[i] > 0) != (d[i + 1] > 0):
            c = caps[i] + (caps[i + 1] - caps[i]) * d[i] / (d[i] - d[i + 1])
            direction = "does worse below, better above" if d[i] > 0 else "does better below, worse above"
            items.append({"kind": "crossing", "capacity": c,
                          "text": f"boundary at capacity {c:.4f} (between {labs[i]} and {labs[i + 1]}; {direction})"})
        i += 1
    if not any(it["kind"].startswith("crossing") for it in items):
        items.insert(0, {"kind": "none", "capacity": None, "text": "no boundary in [0, 1]"})
    return items


def interval_boundary(series):
    """P2-B (b) summary. series: [(capacity_label, verdict)]. Returns dict with the two capacities and text."""
    s = sorted(series, key=lambda t: cap_value(t[0]))
    labs = [c for c, _ in s]
    v = [x for _, x in s]
    worse = [i for i, x in enumerate(v) if x == WORSE]
    beats = [i for i, x in enumerate(v) if x == BEATS]

    def from_index(word):
        k = None
        for i in range(len(v) - 1, -1, -1):
            if v[i] == word:
                k = i
            else:
                break
        return k

    def upto_index(word):
        k = None
        for i in range(len(v)):
            if v[i] == word:
                k = i
            else:
                break
        return k
    out = {"highest_does_worse": labs[worse[-1]] if worse else None,
           "lowest_beats_from": labs[from_index(BEATS)] if from_index(BEATS) is not None else None,
           "pattern": None, "text": None}
    if worse and beats and max(beats) < min(worse):
        out["pattern"] = "reverse"
        a = beats[-1]
        b = from_index(WORSE)
        txt = [f"beats up to capacity {labs[a]}"]
        txt.append(f"does worse from capacity {labs[b]}" if b is not None else "does not do worse at every capacity above")
        lo, hi = a, (b if b is not None else len(v))
    elif worse and beats and max(worse) > min(beats):
        out["pattern"] = "mixed"
        txt = ["mixed: " + "; ".join(f"{labs[i]} {v[i]}" for i in range(len(v)))]
        lo, hi = len(v), len(v)
    else:
        out["pattern"] = "normal"
        txt = []
        txt.append(f"does worse up to capacity {labs[worse[-1]]}" if worse else "never does worse")
        k = from_index(BEATS)
        txt.append(f"beats from capacity {labs[k]}" if k is not None else
                   ("never beats" if not beats else "does not beat at every capacity from any point up to 1"))
        lo = worse[-1] if worse else -1
        hi = k if k is not None else len(v)
    between = [f"{labs[i]}: {v[i]}" for i in range(lo + 1, hi)] if out["pattern"] != "mixed" else []
    if between:
        txt.append("between: " + "; ".join(between))
    out["text"] = "; ".join(txt)
    return out


def chance_expected(n_intervals):
    return 0.025 * n_intervals


def p2u_label(verdicts_by_lambda, anchor=0.057, over=None):
    """P2-U / P3-U on expected loss, per team and capacity, from the descriptive verdicts at the cost ratios.
    over: the ratios the labels are judged on. The run order passes the three non-anchor ratios (0.035, 0.0537,
    0.171); None means all four and is kept for the tests only. The 0.057 verdict enters only the
    break-even lines, which are returned in every mode."""
    lams = sorted(verdicts_by_lambda) if over is None else list(over)
    b = [l for l in lams if verdicts_by_lambda[l] == BEATS]
    w = [l for l in lams if verdicts_by_lambda[l] == WORSE]
    label = "conditional" if (b and not w) else ("not robust" if (b and w) else "")
    breaks = [l for l in sorted(verdicts_by_lambda) if l != anchor and verdicts_by_lambda[l] != verdicts_by_lambda[anchor]]
    return label, b, w, breaks


def section9_reading(lo95, hi95):
    vw = verdict(lo95, hi95)
    return {WORSE: "compounds", BEATS: "cancels (in part)", NODIFF: "additive"}.get(vw, "not defined")

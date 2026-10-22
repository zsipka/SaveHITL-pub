"""
The bootstrap computation, shared by the policy 2 and policy 3 scripts. Plan step 2.1 (Implement and run the sweep;
run register). Designs: policy 2 version 0.4, sections 6, 7, 8.2, 9; policy 3 version 0.13, sections 6, 7, 8.2, 9
(frozen at Gate 1). Build routes M1 to M5 and, for policy 3, M6.

Column groups, one capacity at a time (M1): for one capacity, the per-case vectors of every team instance are
stacked into V (integer-valued float64), and S = counts @ V is formed in row blocks (M2). Row 0 of the sums is the
full sample (every case once), so the point estimate uses exactly the formulas of the resamples. Each measure is
then reduced to its interval ends at once and released; only the interval ends are kept.

Rows exported (one per side, measure, cost ratio and interval level):
  comparison   level | vs_policy_1 | vs_confirm_every_alert | B_minus_A | C_minus_A | bias_x_capacity
               | vs_policy_2 and policy_2_side (policy 3 only)
  version      1 to 5, or "mean of 5 versions"
  level        "95%" (descriptive) or "adjusted" (the deciding results, 2.5/n % and 100 - 2.5/n %)
"""
import numpy as np

from . import boot_core as BC
from . import measures as M

TEAMS = ("A", "B", "C")
VERSIONS = (1, 2, 3, 4, 5)
MEAN = "mean of 5 versions"
REALISTIC = ("0.65", "0.70", "0.75", "0.80", "0.85", "0.90", "10/11", "0.95", "1.00")
DECIDING_MEASURES = (("difference_expected_loss", 0.057), ("difference_accepted_frauds", None),
                     ("difference_age_gap_abs", None))


def deciding(policy, comparison, team, cap, measure, lam):
    """(comparison number, kind) of a deciding result (policy 2 design 8.2; policy 3 design 8.2), else None.
    kind: 'decides', or 'by construction' (policy 2 comparison 5, accepted frauds and signed age gap, P2-K)."""
    key = (measure, lam)
    if comparison == "vs_policy_1" and key in DECIDING_MEASURES:
        if team == "A" and cap == "1.00":
            return 1, "decides"
        if team == "B" and cap in REALISTIC:
            return 2, "decides"
        if team == "C" and cap in REALISTIC:
            return 3, "decides"
    if policy == 2 and cap == "0.75":
        if comparison == "B_minus_A" and key in DECIDING_MEASURES:
            return 4, "decides"
        if comparison == "C_minus_A":
            if key == ("difference_expected_loss", 0.057):
                return 5, "decides"
            if key in (("difference_accepted_frauds", None), ("difference_age_gap_signed", None)):
                return 5, "by construction"
    if policy == 3 and comparison == "vs_policy_2" and key in DECIDING_MEASURES:
        if team == "A" and cap == "1.00":
            return 4, "decides"
        if team == "B" and cap == "0.75":
            return 5, "decides"
        if team == "C" and cap == "0.75":
            return 6, "decides"
    return None


class Emitter:
    def __init__(self, policy, n_deciding, run_id):
        self.policy, self.run_id = policy, run_id
        self.adj = BC.adjusted_percentiles(n_deciding)
        self.rows = []

    def emit(self, comparison, team, version, cap, K, measures):
        for (measure, lam), (x, ok) in measures.items():
            point = float(x[0]) if ok[0] else float("nan")
            xb, okb = x[1:], ok[1:]
            dec = deciding(self.policy, comparison, team, cap, measure, lam)
            levels = [("95%", 2.5, 97.5)]
            if dec:
                levels.append(("adjusted", self.adj[0], self.adj[1]))
            for lvl, ql, qh in levels:
                lo, hi, used = BC.interval(xb, okb, ql, qh)
                self.rows.append({
                    "policy": self.policy, "comparison": comparison, "team": team, "version": version,
                    "capacity_label": cap, "K": K, "lambda": "" if lam is None else lam, "measure": measure,
                    "point_estimate": point, "level": lvl, "percentile_low": ql, "percentile_high": qh,
                    "ci_low": lo, "ci_high": hi, "resamples_used": used, "resamples_dropped": int(len(xb) - used),
                    "deciding_comparison": dec[0] if dec else "", "deciding_kind": dec[1] if dec else "",
                    "run_id": self.run_id})


CONTRAST_KEEP = ("expected_loss_total", "regulatory_exposure_accepted_frauds_count", "fairness_exposure_age_gap_abs",
                 "fairness_exposure_age_gap_signed", "overall_false_rejection_rate", "false_rejections_50_plus_count")


class Mean5:
    """Running mean of the five versions, per resample: x1 + x2 + ... + x5 in version order, then divided by 5
    (the same operations as sum() / 5); defined where all five are. Keeps one array per measure, not five."""

    def __init__(self):
        self.s, self.n = None, 0

    def add(self, d):
        if self.s is None:
            self.s = {k: (x.copy(), ok.copy()) for k, (x, ok) in d.items()}
        else:
            assert set(d) == set(self.s)
            self.s = {k: (self.s[k][0] + d[k][0], self.s[k][1] & d[k][1]) for k in self.s}
        self.n += 1

    def get(self):
        assert self.n == 5
        return {k: (x / 5.0, ok) for k, (x, ok) in self.s.items()}


def _pick(meas, keep):
    return {k: v for k, v in meas.items() if k[0] in keep}


LEVEL_KEEP_P2 = None    # all level measures


def run(counts, case_ids, label, age50, p1, blocks, caps, policy, lams, n_deciding, run_id, block_rows=2000,
        log=print):
    """counts (B, N) uint8; blocks[(team, version, cap_label)] = {column: int64 array in case order}.
    Returns (rows, record)."""
    N = counts.shape[1]
    assert len(case_ids) == N and np.all(np.diff(case_ids) > 0)
    em = Emitter(policy, n_deciding, run_id)
    rec = {"block_rows": block_rows, "storage": {"counts": "uint8", "per_case_vectors": "integer-valued float64",
           "row_block_conversion": "uint8 -> float64 per block (G-c: no arithmetic in 8 bits)",
           "sums": "float64, exact integers"}, "groups": "one capacity at a time (all 15 team instances)",
           "max_abs_parts_minus_difference": 0.0, "g3_dropped": None, "bias_x_capacity_max_I_by_construction": {}}

    # constants: one group (not seed-dependent)
    cv = M.const_vectors(label, age50, p1)
    Vc = np.stack([cv[k] for k in M.CONST_NAMES], axis=1).astype(np.float64)
    Sc = BC.resample_sums(counts, Vc, block_rows, with_point=True)
    c = {k: Sc[:, j] for j, k in enumerate(M.CONST_NAMES)}
    del Sc
    g3_ok = (c["lo"][1:] > 0) & (c["ly"][1:] > 0)
    rec["g3_dropped"] = int((~g3_ok).sum())
    p1lev = M.policy_1_levels(c, lams)
    cea = M.confirm_every_alert_levels(c, lams)
    sec9 = {}                                      # (metric, cap, version) -> C - A array (point + resamples)

    for cap in caps:
        lab, K = cap["label"], cap["K"]
        names, cols = [], []
        for t in TEAMS:
            for v in VERSIONS:
                sv = M.side_vectors(blocks[(t, v, lab)], label, age50, p1, policy)
                for k, vec in sv.items():
                    names.append((t, v, k)); cols.append(vec)
        V = np.stack(cols, axis=1).astype(np.float64)
        del cols
        S = BC.resample_sums(counts, V, block_rows, with_point=True)
        del V
        col = {nm: j for j, nm in enumerate(names)}

        def side(t, v):
            keys = [k for (tt, vv, k) in names if tt == t and vv == v]
            return {k: S[:, col[(t, v, k)]] for k in keys}

        lev = {}                                   # levels kept for the team contrasts only (trimmed)
        for t in TEAMS:
            m_lev, m_d1, m_cea, m_q, m_dq = Mean5(), Mean5(), Mean5(), Mean5(), Mean5()
            for v in VERSIONS:
                s = side(t, v)
                L = M.levels(s, c, lams, K, policy)
                if t != "B":
                    L.pop(("team_b_share_disagreements_deferred", None), None)
                lev[(t, v)] = {k: L[k] for k in L if k[0] in CONTRAST_KEEP}
                D1 = M.difference(L, p1lev, lams)
                Dc = {("difference_expected_loss", lam): (L[("expected_loss_total", lam)][0] - cea[("expected_loss_total", lam)][0],
                                                          L[("expected_loss_total", lam)][1]) for lam in lams}
                if policy == 2:
                    SP = M.split_policy_2_vs_policy_1(s, c, lams)
                    for lam in lams:
                        dev = SP[("reviewed_part_expected_loss", lam)][0] + SP[("unreviewed_part_expected_loss", lam)][0] - D1[("difference_expected_loss", lam)][0]
                        rec["max_abs_parts_minus_difference"] = max(rec["max_abs_parts_minus_difference"], float(np.abs(dev).max()))
                    dev = SP[("reviewed_part_accepted_frauds", None)][0] + SP[("unreviewed_part_accepted_frauds", None)][0] - D1[("difference_accepted_frauds", None)][0]
                    rec["max_abs_parts_minus_difference"] = max(rec["max_abs_parts_minus_difference"], float(np.abs(dev).max()))
                    D1.update(SP)
                else:
                    Q = M.side_policy_2_levels(s, c, lams)
                    DQ = M.difference(L, Q, lams)
                    SP3 = M.split_policy_3_vs_policy_2(s, lams)
                    for lam in lams:
                        dev = SP3[("classifier_part_expected_loss", lam)][0] + SP3[("reviewed_part_expected_loss", lam)][0] - DQ[("difference_expected_loss", lam)][0]
                        rec["max_abs_parts_minus_difference"] = max(rec["max_abs_parts_minus_difference"], float(np.abs(dev).max()))
                    dev = SP3[("classifier_part_accepted_frauds", None)][0] + SP3[("reviewed_part_accepted_frauds", None)][0] - DQ[("difference_accepted_frauds", None)][0]
                    rec["max_abs_parts_minus_difference"] = max(rec["max_abs_parts_minus_difference"], float(np.abs(dev).max()))
                    DQ.update(SP3)
                    Qp = _pick(Q, ("fairness_exposure_age_gap_abs", "fairness_exposure_age_gap_signed", "overall_false_rejection_rate"))
                    em.emit("policy_2_side", t, v, lab, K, Qp)
                    em.emit("vs_policy_2", t, v, lab, K, DQ)
                    m_q.add(Qp); m_dq.add(DQ)
                    del Q, DQ, SP3, Qp
                em.emit("level", t, v, lab, K, L)
                em.emit("vs_policy_1", t, v, lab, K, D1)
                em.emit("vs_confirm_every_alert", t, v, lab, K, Dc)
                m_lev.add(L); m_d1.add(D1); m_cea.add(Dc)
                del L, D1, Dc, s
            em.emit("level", t, MEAN, lab, K, m_lev.get())
            em.emit("vs_policy_1", t, MEAN, lab, K, m_d1.get())
            em.emit("vs_confirm_every_alert", t, MEAN, lab, K, m_cea.get())
            if policy == 3:
                em.emit("policy_2_side", t, MEAN, lab, K, m_q.get())
                em.emit("vs_policy_2", t, MEAN, lab, K, m_dq.get())
            del m_lev, m_d1, m_cea, m_q, m_dq
        # team contrasts within a version (policy 2 comparisons 4 and 5; policy 3 P3-X), and section 9 inputs
        for t, name in (("B", "B_minus_A"), ("C", "C_minus_A")):
            m_c = Mean5()
            for v in VERSIONS:
                Dv = M.difference(lev[(t, v)], lev[("A", v)], lams)
                m_c.add(Dv)
                em.emit(name, t, v, lab, K, Dv)
                if t == "C" and lab in ("0.75", "1.00"):
                    sec9[("fairness_exposure_age_gap_signed", lab, v)] = Dv[("difference_age_gap_signed", None)]
                    sec9[("false_rejections_50_plus_count", lab, v)] = Dv[("difference_false_rejections_50_plus", None)]
                    sec9[("expected_loss_total_0.057", lab, v)] = Dv[("difference_expected_loss", 0.057)]
            em.emit(name, t, MEAN, lab, K, m_c.get())
        del S, lev
        log(f"capacity {lab} done; rows so far {len(em.rows)}; peak {BC.peak_rss()} B")

    # section 9: I = [m(C, 0.75) - m(A, 0.75)] - [m(C, 1) - m(A, 1)], per version and for the mean of the five
    for metric in ("fairness_exposure_age_gap_signed", "false_rejections_50_plus_count", "expected_loss_total_0.057"):
        per = []
        for v in VERSIONS:
            x75, o75 = sec9[(metric, "0.75", v)]; x1, o1 = sec9[(metric, "1.00", v)]
            per.append({("bias_x_capacity_I_" + metric, None): (x75 - x1, o75 & o1)})
            em.emit("bias_x_capacity", "C", v, "0.75 vs 1.00", "", per[-1])
            if policy == 2 and metric != "expected_loss_total_0.057":
                xs = (x75 - x1)[o75 & o1]
                rec["bias_x_capacity_max_I_by_construction"][f"{metric}, version {v}"] = float(xs.max())
        em.emit("bias_x_capacity", "C", MEAN, "0.75 vs 1.00", "", M.mean_of_five(per))
    return em.rows, rec

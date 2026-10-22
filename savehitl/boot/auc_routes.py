"""
Two independent routes to the area under the receiver operating characteristic curve, with case weights (the study's
module, unchanged below this description).

Reading "weighted": case weight 0.057 (the `lambda` of dataset_cfg.yaml) on every legitimate alert and 1 on every fraud,
computed exactly, not by resampling. The weight depends on the fraud label of the alert, not on the class being ranked
(decision correct or not), so both classes carry mixed weights.

Route 1, `auc_sk`: scikit-learn 0.24.2 `roc_auc_score(..., sample_weight=w)` (weighted cumulative sums at each distinct
score, trapezoid area; a tied pair counts one half).
Route 2, `auc_rank`: weighted Mann-Whitney, by sorting into groups of equal score:
    AUC = sum over positives i of w_i * (W0(score < s_i) + 0.5 * W0(score == s_i)) / (W1 * W0)
where W1, W0 are the total weights of the positives and negatives. No scikit-learn code is used.

Self-tests (`self_test`), synthetic data only: weights all 1 equal the unweighted routes; integer weights equal
duplicating rows; scaling all weights leaves the value unchanged; ties; the two routes agree.
"""
import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score


def _prep(c, s, w):
    c = np.asarray(c, dtype=int); s = np.asarray(s, dtype=float)
    w = np.ones(len(c), dtype=float) if w is None else np.asarray(w, dtype=float)
    if not (len(c) == len(s) == len(w)) or np.any(w < 0) or not np.all(np.isfinite(s)):
        raise ValueError("lengths differ, a negative weight, or a non-finite score")
    if not set(np.unique(c)) <= {0, 1}:
        raise ValueError("class must be 0 or 1")
    return c, s, w


def auc_sk(c, s, w=None):
    c, s, w = _prep(c, s, w)
    if w[c == 1].sum() == 0 or w[c == 0].sum() == 0:
        return np.nan
    return float(roc_auc_score(c, s, sample_weight=w))


def auc_rank(c, s, w=None):
    c, s, w = _prep(c, s, w)
    W1 = float(w[c == 1].sum()); W0 = float(w[c == 0].sum())
    if W1 == 0 or W0 == 0:
        return np.nan
    u, inv = np.unique(s, return_inverse=True)
    w0 = np.bincount(inv, weights=w * (c == 0), minlength=len(u))
    credit = (np.cumsum(w0) - w0) + 0.5 * w0          # negatives strictly below + half of those tied
    return float(np.sum(w[c == 1] * credit[inv[c == 1]]) / (W1 * W0))


def auc_rank_unweighted(c, s):
    """The existing unweighted rank-sum of p3g_c_ranking.py, kept for the self-test."""
    c = np.asarray(c, dtype=int); r = rankdata(s); n1 = int(c.sum()); n0 = len(c) - n1
    return float((r[c == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def self_test(tol=1e-12, seed=0):
    rng = np.random.RandomState(seed)
    out = {}
    n = 5400
    c = rng.binomial(1, 0.7, n); fraud = rng.binomial(1, 0.1, n)
    s = np.round(rng.rand(n), 3)                        # rounded, so there are many ties
    w = np.where(fraud == 1, 1.0, 0.057)
    out["routes_agree_weighted"] = abs(auc_sk(c, s, w) - auc_rank(c, s, w))
    out["ones_equal_unweighted_sk"] = abs(auc_sk(c, s, np.ones(n)) - float(roc_auc_score(c, s)))
    out["ones_equal_unweighted_rank"] = abs(auc_rank(c, s, np.ones(n)) - auc_rank_unweighted(c, s))
    k = rng.randint(1, 4, n)                            # integer weights = rows repeated k times
    cd, sd = np.repeat(c, k), np.repeat(s, k)
    out["integer_weights_equal_duplication_sk"] = abs(auc_sk(c, s, k) - float(roc_auc_score(cd, sd)))
    out["integer_weights_equal_duplication_rank"] = abs(auc_rank(c, s, k) - auc_rank_unweighted(cd, sd))
    out["scale_invariance_rank"] = abs(auc_rank(c, s, w) - auc_rank(c, s, 17.0 * w))
    out["scale_invariance_sk"] = abs(auc_sk(c, s, w) - auc_sk(c, s, 17.0 * w))
    out["all_tied_is_half"] = abs(auc_rank(c, np.zeros(n), w) - 0.5) + abs(auc_sk(c, np.zeros(n), w) - 0.5)
    ok = all(v <= tol for v in out.values())
    return ok, out

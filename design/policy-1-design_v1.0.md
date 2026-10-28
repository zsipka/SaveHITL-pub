Version: 1.0 | 8 October 2026 | Status: Approved

# Policy 1 — Full automation (the baseline)

**Contents**

- [1. What this policy is for](#1-what-this-policy-is-for)
- [2. The policy in one paragraph](#2-the-policy-in-one-paragraph)
- [3. What is used, and why](#3-what-is-used-and-why)
- [4. How Classifier *h* decides](#4-how-classifier-h-decides)
- [5. The sweep: cost ratio λ only](#5-the-sweep-cost-ratio-λ-only)
- [6. What is measured](#6-what-is-measured)
- [7. Use constraint and integrity of the result](#7-use-constraint-and-integrity-of-the-result)
- [8. Results tables and figures](#8-results-tables-and-figures)
- [9. What every run records](#9-what-every-run-records)
- [10. Size](#10-size)
- [11. Limits](#11-limits)
- [Sources](#sources)

**Terminology.** A *scenario* is one policy run with one team: seven in all. Policy 1 involves no human, so it has no team and forms a single scenario. Policies 2 (review everything) and 3 (analyst-aware deferral), each with teams A, B and C, give six more. There is one design document per policy.

**Models used here** (names as in the framework's documentation):

| Component | What it is |
|---|---|
| **Classifier *h*** | The already-trained LightGBM model that decides each alert: confirm or dismiss |
| **Alert Model** | The LightGBM model whose score above a 5% false-positive cut-off turns an application into an alert. **Not used to decide anything in policy 1**; "confirm every alert" (its flag) is shown only as a reference figure |

---

## 1. What this policy is for

| Project outline statement | Role of policy 1 |
|---|---|
| Policies compared: "full automation, with no human review" | This policy |
| Hypothesis: "calibrated deferral achieves lower risk than … full automation"; naive HITL "can be worse than full automation". This study tests the first part with analyst-aware deferral in place of calibrated deferral (policy 3 design, section 1) | The reference that every other scenario is compared with |
| Refutation: "deferral fails to outperform automation …", "naive HITL never falls below automation" | Both clauses are measured against this baseline |

Policy 1 tests nothing by itself. Its job is to be a correct and fixed baseline. The baseline is Classifier *h*, the re-used model that decides alerts. How it compares with "confirm every alert" at each cost ratio is reported by the policy 1 sweep.

## 2. The policy in one paragraph

Take the 4,457 alerts of the test month. Classifier *h* decides each one, confirm or dismiss, with its built-in rule and no human involved. Capacity and team play no role. The decisions are computed once; their cost is then counted at each cost ratio of the sweep.

## 3. What is used, and why

In line with the project outline's aim to minimise re-training (Method), nothing is retrained and nothing new is fitted.

The data's months are numbered from 0 (file months).

| Element | What | Why | Source |
|---|---|---|---|
| Cases | The 4,457 alerts of file month 7 | The benchmark's test month; the only month not used to build any of the framework's models | Paper p. 7, Fig. 2 (month 8 is the test month for every component); Paper p. 12 (test split = month 8, one batch of 4,457) |
| The model | **Classifier *h*** | The re-used model that decides alerts, chosen as the baseline. How it compares with "confirm every alert" at each cost ratio is reported by the policy 1 sweep | Paper pp. 19–20 ("Classifier h": LightGBM, trained on alerts of paper months 4–6) |

**Data source:** the dataset's alerts file is the only source of the cases, their labels, their features and the alert score. Policy 1 itself does not use the alert score.

## 4. How Classifier *h* decides

1. Score s(x) = sigmoid(raw score + 1.9822), with the offset stored with the model (Paper p. 23, Table 4, selected initial score 1.982).
2. **Rule: reject if s(x) ≥ 0.5**, at every cost ratio.
3. The model was trained with weight 0.057 on legitimate cases and 1 on frauds (Paper pp. 19–20). This rule is therefore cost-optimal only at λ = 0.057 (Paper p. 6, eq. 7). At every other cost ratio the same decisions are kept, without re-optimising them; see the use constraint in section 7 and limit 3 in section 11.

## 5. The sweep: cost ratio λ only

**Definition.** The *sweep* is the fixed list of settings at which a scenario is run. The term is the project outline's ("the full sweep is reported", Integrity of the result). For policy 1 the only setting that varies is the cost ratio λ. For policies with reviewers, review capacity is a second setting.

λ = cost of a false rejection ÷ cost of a missed fraud. The project outline makes it a parameter to be "set, and varied". In policy 1, λ changes only how the fixed decisions are costed. Policy 1 is costed at the four values below to give the baseline. The cost-ratio sweep for policies 2 and 3 is set in their designs.

| λ | Why |
|---|---|
| 0.035 | Lies inside the range the data suggest, roughly 0.03–0.045 (limit 2) |
| 0.0537 | The ratio implied by the cut-off actually stored (below) |
| **0.057 — the anchor** | The ratio Classifier *h* was trained for (below) |
| 0.171 | Three times the anchor: false rejections relatively costlier |

**The sweep:** four values, 0.035, 0.0537, 0.057 (anchor) and 0.171. Consequence: of the data-implied range of roughly 0.03–0.045 (limit 2), only 0.035 is tested. Results say nothing about cost ratios below 0.035, or between 0.035 and 0.0537.

**Where 0.0537 and 0.057 come from.** The Alert Model flags cases above the cut-off t that gives a 5% false positive rate (Paper p. 6, "Task"; p. 7, top; p. 11). If that cut-off is cost-optimal, λ = t/(1 − t) (Paper p. 6, eq. 7–8). The stored cut-off is t = 0.05096879788436479, which gives 0.0537. **Confirmed from the data:** t recomputed from the month-3 scores equals the stored value exactly; it flags 5.00% of month-3 legitimate applications; the applications of months 3–7 scoring above t are exactly the 30,622 alerts; t/(1 − t) = 0.053706135025636884. The anchor is 0.057, with 0.0537 also swept. 0.057 is the ratio Classifier *h* was trained for (Paper pp. 19–20) and is the only ratio at which the rule of section 4 is cost-optimal.

## 6. What is measured

On the month-7 alerts, per λ.

| Measure | Definition | Project outline link |
|---|---|---|
| **Expected loss** | Σ over cases of [λ·1(rejected, legitimate) + 1(accepted, fraud)], with the cost of a missed fraud set to 1 (Paper p. 4, eq. 2–3). Total and per case | Risk axis 1 |
| **Regulatory exposure** | Count of accepted frauds, and the miss rate: accepted frauds ÷ all frauds among the test-month alerts, that is, false negatives ÷ (false negatives + true positives), also called the false negative rate. Both lower is better. Wherever the rate is reported, one sentence also states the share stopped (e.g. "5.6% let through, i.e. 94.4% stopped"). Does not depend on λ in policy 1 | Risk axis 2 |
| **Fairness exposure** | False rejection gap: false positive rate of applicants aged 50 or over minus that of applicants under 50, among legitimate alerts. It is the paper's protected group: the paper treats age as the protected attribute and gives its experts varying levels of bias against older applicants (Paper p. 8). Closer to zero is better. A positive figure means applicants aged 50 or over are wrongly rejected more often. Does not depend on λ in policy 1 | Risk axis 3 |

The project outline's four monitoring indicators (reviewer override rate, capacity utilisation, loss avoided per review, subgroup disparity) are **not defined** for this policy, because nothing is reviewed. In policies 2 and 3, this study computes subgroup disparity on reviewed cases.

Each measure is reported with a 95% case-bootstrap interval (B = 1,000). Policy 1's decisions are deterministic (no random seed). The bootstrap seed is recorded (section 9). The intervals use the first 1,000 rows of the shared index matrix, set out in the policy 2 design, section 7.

**Reference figure, not a policy:** "confirm every alert" (every application rejected; the flag of the Alert Model stands), with the same three measures per λ. Shown beside policy 1 so that the reader sees both automated options.

**Export needed by the other policies.** The per-case decision of policy 1, and its per-case cost at each λ, keyed by case. Policies 2 and 3 compare against it case by case.

## 7. Use constraint and integrity of the result

Policy 1 supports no conclusion about human oversight. Its use constraint limits what other policies may claim against it.

| Id | Rule, checkable from the tables | How it applies |
|---|---|---|
| **P1-U** Use constraint (follows from the rule of section 4) | At λ ≠ 0.057, the baseline is not re-optimised for the cost ratio. Any statement that another policy beats automation at λ ≠ 0.057 must carry the qualifier "against an automation baseline not re-optimised for this cost ratio". No conclusion that a policy beats automation **robustly across cost ratios** may be drawn; results away from 0.057 can support only "conditional (stated range)" or "not robust". How results of policies 2 and 3 away from 0.057 are read is set in their designs (rules P2-U and P3-U) | Applies to the decision rules of policies 2 and 3 |

**Integrity of the result.**

| Control | What it means | Where it is set |
|---|---|---|
| **Everything reported** | Every combination of policy, team and setting is reported, including those where the result is unfavourable to the hypothesis | Project outline, Integrity of the result |
| **Uncertainty shown** | Every figure is reported with a 95% case-bootstrap range. Policy 1 re-draws the cases 1,000 times (section 6). Policies 2 and 3 re-draw them 50,000 times, and widen their deciding ranges as set in their section 7 | Section 6 |
| **Every run recorded** | Each run records what was run and on which data, when, the result, how long it took and the most memory it used, so that any figure can be traced to the run that produced it and re-produced | Section 9 |

## 8. Results tables and figures

| Id | Content | Serves |
|---|---|---|
| P1-T2 | Baseline per λ: the three measures with intervals; "confirm every alert" beside it | Reference for all scenarios |
| P1-T3 | Runtime and peak memory per run | Run record |
| P1-F1 | The three measures vs. λ, policy 1 and "confirm every alert"; λ = 0.057 marked as the anchor | Reference for all scenarios; P1-U |

## 9. What every run records

1. Run identifier; date and time (Swiss).
2. Versions of Python, LightGBM, scikit-learn, NumPy and pandas, as pinned in `environment.colab.yml`.
3. Checksums of the alerts file and of the Classifier *h* model file.
4. Parameters: list of λ, bootstrap seed, B.
5. **Result:** location of the per-case decision and cost file; the measures of section 6.
6. **Runtime** (wall clock, seconds).
7. **Peak memory:** maximum resident set size, in bytes.
8. Where it is kept: each step's runtime and peak memory in the run's `logs/` folder; the checksums of item 3 in `results/input_checksums.csv`.

## 10. Size

One set of 4,457 decisions, costed at 4 cost ratios, plus the reference figure. A single run. Negligible.

## 11. Limits

1. One alert-generation model, one test month: 4,457 alerts, about 711 frauds (0.1595 × 4,457).
2. The cost ratio is implied by the cut-off of the Alert Model, not observed. Reading t/(1 − t) as a cost ratio assumes the alert score is a true fraud probability at t. Near t it overstates it: in month 3, scores of 0.04–0.06 average 0.045–0.055 against actual fraud rates of 0.028–0.043. The data therefore suggest an implied ratio of roughly 0.03–0.045 (arithmetic: p/(1 − p) with p the actual fraud rate near t), lower than both 0.0537 and 0.057. The estimate is rough: wide bins, 124 frauds in the two bins around t, and month 3 is the month on which t was set and on which the Alert Model was validated, its search for settings stopping early on that month's result (Paper p. 6; p. 7, Table 1; the paper's month 4). This range is partly covered by the sweep: only 0.035 lies inside it.
3. Away from λ = 0.057, the automation baseline is not re-optimised for the cost ratio (use constraint P1-U). Its effect is not measured.

## Sources

| Short name | Source |
|---|---|
| Paper | Alves et al., "A benchmarking framework and dataset for learning to defer in human-AI decision-making", *Scientific Data* 12:506, 2025, cited by page. Printed page numbers equal PDF page numbers. Paper months are numbered from 1 (file month + 1) |
| Project outline | The project outline, "Save the Human (in the loop): when does human oversight of AI actually reduce risk?", version 0.9, 18 September 2026 |
| Policy 2 design | [policy-2-design_v1.0.md](policy-2-design_v1.0.md) |
| Policy 3 design | [policy-3-design_v1.0.md](policy-3-design_v1.0.md) |

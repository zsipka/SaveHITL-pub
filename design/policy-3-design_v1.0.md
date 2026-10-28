Version: 1.0 | 22 October 2026 | Status: Approved

# Policy 3 — Analyst-aware deferral

**Contents**

- [1. What this policy is for](#1-what-this-policy-is-for)
- [2. The policy](#2-the-policy)
  - [2.1 The teams' behaviour](#21-the-teams-behaviour)
    - [Team A: behaviour diagram](#team-a-behaviour-diagram)
    - [Team B: behaviour diagram](#team-b-behaviour-diagram)
    - [Team C: behaviour diagram](#team-c-behaviour-diagram)
  - [2.2 What follows from the trees (arithmetic, not results)](#22-what-follows-from-the-trees-arithmetic-not-results)
- [3. What is used](#3-what-is-used)
- [4. The three teams](#4-the-three-teams)
- [5. The sweep](#5-the-sweep)
- [6. What is measured](#6-what-is-measured)
- [7. Comparison method](#7-comparison-method)
- [8. Checks and decision rules](#8-checks-and-decision-rules)
  - [8.1 Checks](#81-checks)
  - [8.2 Main comparisons](#82-main-comparisons)
  - [8.3 Decision rules](#83-decision-rules)
- [9. Bias × capacity](#9-bias--capacity)
- [10. Results tables and figures](#10-results-tables-and-figures)
- [11. What every run records](#11-what-every-run-records)
- [12. Size](#12-size)
- [13. Limits](#13-limits)
- [Sources](#sources)
  - [Plain terms used in the body, and what they stand for](#plain-terms-used-in-the-body-and-what-they-stand-for)

**How to read this design.** The body is written for a human reader. Every term is introduced before it is used: the terms used throughout are defined below, and the others where they first appear. Page references to the paper are given in the body.

**Policy 3 in brief** (the terms are defined just below; the decision trees of section 2.1 are the master, and where this summary and the trees differ, the trees hold).
- **What it tests.** Whether sending each alert to whoever is most likely to decide it correctly, a simulated reviewer or the model, gives lower risk than the model alone (policy 1) and than reviewing every alert (policy 2).
- **What happens to an alert.** The 4,457 alerts of the test month are taken one by one, in a random order. For each alert, a set of models (the router) estimates how likely each of the team's ten reviewers is to decide it correctly; the model's own confidence is its estimate. The alert goes to the reviewer with the highest estimate if that estimate is strictly higher than the model's and the reviewers still have room within their shared limit. Otherwise the model decides it. No alert is left undecided.
- **Who decides.** On an alert sent to the model, the model's decision is final. On an alert sent to a reviewer, the team's rule gives the final decision: team A keeps the reviewer's decision; where the reviewer and the model disagree, team B follows the model about 4 times in 5. Team C's alerts of applicants aged 50 or over that the model would confirm are confirmed by the model, without review; its other alerts are routed as team A's.
- **What is checked.** Before any result is used: that the reviewers keep the stored experts' weights, α and target costs, with the age weight at 0, and are made a second time and come out identical; that the five teams are disjoint and use all 50 reviewers; that the router's training files can be made again identically, hold only each team's reviewers, and that the router's models and month-7 prediction file are the ones defined; how well the router ranks the reviewers, and, if it is no better than chance, no policy 3 figure is used until that is resolved; that every alert went where the trees send it; and that the verdicts are recomputed correctly (section 8.1).
- **What decides.** 66 results, against policy 1 and policy 2, at the cost ratio 0.057, judged by the rules of sections 8.2 and 8.3.

**Terms used throughout.**
- **Alerts and applications.** The alert model flags some applications as possible fraud; each flagged application is an **alert**. An alert is **confirmed** or **dismissed**. An application is **accepted** or **rejected**. Confirming an alert rejects the application; dismissing it accepts the application. "Accepts" or "rejects" on its own means the application.
- **File months.** The data's months are numbered from 0. Results are judged on file month 7, which holds 4,457 alerts.
- **Experts and twins.** The experts are the framework's simulated reviewers. The framework ships 50 of them, the **stored experts**. The project regenerated them with the framework's own generator, with the weight on age set to 0 and fitted on file months 3 to 6; these are the **twins**. In policy 3, every expert is a twin.
- **Classifier.** The model of policy 1. It gives each alert a score h between 0 and 1 and confirms the alert when h is 0.5 or more.
- **Router.** A set of models, one per expert, that estimates for each alert how likely each expert is to decide it correctly (section 2, item 3).
- **OvA and DeCCaF** are the framework's names for its two routing methods. OvA routes one alert at a time on one model per expert; DeCCaF assigns a whole batch at once. Policy 3 uses OvA.
- **Decision-maker.** Any of the eleven that can decide an alert in policy 3: the team's ten experts and the classifier.
- **Teams, versions and team instances.** Teams A, B and C apply three different rules to the decisions of the same ten experts (section 2.1). A **version** is one fixed set of ten experts ("Versions", below). One team in one version is a **team instance**: 15 in all.
- **Capacity** is the largest share of the 4,457 alerts the team's experts may review, from 0 to 1. **K** is that share as a number of alerts, rounded down. In policy 3, K is a ceiling, not a quota.
- **Routing** is sending each alert to one decision-maker, before any expert has looked at it (section 2).
- **Seed, review order and deference draw.** Each seed (1 to 5) fixes one random order in which the alerts are taken, the **review order**, and one random number per alert that team B's rule uses, the **deference draw**; both as in policy 2.
- **Team C's test.** An alert meets it when the applicant is aged 50 or over and the classifier would confirm the alert (section 2.1).
- **λ (the cost ratio)** is the cost of rejecting a legitimate application, measured against the cost of accepting a fraudulent one, which counts as 1. The main value is 0.057.
- **Difference** between two policies means the first one's result minus the second one's, on the same alerts. On all three measures (expected loss, accepted frauds, and the absolute age gap in wrongly rejected applications between applicants aged 50 or over and those under 50) lower is better, so a negative difference means the first policy does better.
- **Replay** means applying the stored decisions of the experts and of the classifier to the alerts, under a policy's rules. Nothing is re-trained or re-predicted in a replay.

**Models used here** (names as in the framework's documentation):

| Component | Role in policy 3 |
|---|---|
| **Synthetic Experts**, regenerated as unbiased twins | The reviewers, as in policy 2. Their own decision on a reviewed alert is the input of the team rules |
| **Classifier *h*** | Policy 1, the baseline. In policy 3 it is also one of the decision-makers an alert can be routed to, with no capacity limit |
| **OvA Classifiers** | The router. For each alert and each expert, it estimates the chance that this expert decides the alert correctly (the framework's router, trained by the framework's own procedure, including its search for settings, on the twins' decisions, on training files built for the drawn teams by the framework's script; router per seed) |
| **Alert Model** | Its flag turns an application into an alert, as in policies 1 and 2 |

**Basis.** The aim is to compare oversight options, not to build the best model. Policy 3 reuses everything policies 1 and 2 have settled: the alerts, the models, the twins, teams A, B and C with their rules and five versions, the review order, the deference draws, the capacity grid and seeds, the measures, the comparison method, the checks and the run record. It changes only what its routing needs. Policy 2's dealing, which shares the reviewed alerts out to the experts in turn, is not used: in policy 3 the experts share one pool. Every reference to policy 1 or policy 2 means its design, version 1.0 (Sources). Where this design says "as policy 2", the policy 2 design is the master and is not restated.

**Scenarios.** A scenario is one policy run with one team: seven in all (policy 1 design). Policy 3 with teams A, B and C gives three of them.

**Versions** (as policy 2 section 4, "What a version is", which is the master). The 50 twins are split at random into five disjoint teams of ten, the **drawn teams** 1 to 5 (policy 2 section 4, "What a version is"). Version r is drawn team r. Within a version, teams A, B and C are the same ten twins with different rules for the final decision. Every comparison is made within a version, and the five versions repeat the experiment with different experts. In policy 3, a version also fixes which router is used: the router trained for drawn team r (section 2, item 3). Unlike in policy 2, the mean of the five versions does not give each twin the same weight, because the shared pool lets the best-scoring twins take most alerts (limit 9).

---

## 1. What this policy is for

| Project outline statement | Role of policy 3 |
|---|---|
| Aspirational extension, adopted in place of calibrated deferral: "Analyst-aware deferral, routing each case to the reviewer most likely to be correct" | This policy. It takes the place of the project outline's third compared policy, "calibrated deferral, in which only cases of high model uncertainty are routed, within capacity" |
| Hypothesis: "Across realistic review capacity levels, calibrated deferral achieves lower risk than both full automation and naive review-everything HITL" | Tested with analyst-aware deferral in place of calibrated deferral. Against policy 1: comparisons 1 to 3; against policy 2: comparisons 4 to 6 (section 8.2) |
| Refutation clause 1: "the hypothesis is refuted if deferral fails to outperform automation at any capacity level" | Decided here (rule P3-R1; strict reading) |
| The three review teams: "a standard mixed team"; a team "whose capacity is materially exceeded and is biased against certain applicant attribute(s)"; a team "whose members largely agree with the model score" | As policy 2, sections 1 and 4 |

**The study's own criteria.** The project outline's objective is to "Define what 'appropriately applied' human-in-the-loop … means in measurable terms". To make it measurable, this study proposes four criteria: a case reaches a human only if (1) the reviewer is more likely than the model to be correct; (2) the volume routed fits the actual review capacity; (3) the expected loss avoided exceeds the cost of review; (4) the reviewer has the information and time to disagree with the model. Policy 3 treats them as follows:
- **Criterion 1** holds by construction as the router sees it: an expert takes an alert only if its score is strictly above the classifier's (section 2). Whether it holds in fact is measured (section 6).
- **Criterion 2** holds by construction: at most K alerts are reviewed.
- **Criterion 3** is measured, not enforced: loss avoided per review is reported as the break-even cost of one review.
- **Criterion 4** is observable only through the override rate (policy 2 design, limit 1).

**The study's own aim.** This study's priority for policy 3 is to find the capacity boundaries at λ = 0.057 (rule P3-B).

## 2. The policy

The alerts are the 4,457 alerts of file month 7, handled as one batch, as in policy 2 section 2. Everything below is run for each team, team version, capacity and seed. What each team does with an alert is specified only by the trees of section 2.1; this section defines what the trees use.

1. **The experts' pool.** K is the capacity times 4,457, rounded down, as in policy 2 section 2, item 1. The team's ten experts share one pool of K alerts, with no limit per expert. An expert's review uses one place in the pool, whatever the team rule then decides.
2. **The classifier has no limit.** It is a machine, so it can decide any number of alerts. Every alert the experts do not take is decided by the classifier.
3. **Scores.** Each alert gets eleven scores, one per decision-maker. A score is an estimate of the chance that this decision-maker decides the alert correctly.
   - **An expert's score**, also called the expert's **own score** to set it apart from the team-aware score below, is the router's estimate that this expert's own decision on the alert, before any team rule, will be right. The experts do not produce scores; the router, a set of models with one per expert, estimates them from the details of the alert. The expert's true probability of error, known only inside the simulation, is not used.
   - **Which router models.** The router is trained 25 times: once for each of the five drawn teams, and five times per team, with the framework's five shuffles of the training cases (section 3). Here, team version r uses the router of drawn team r, and seed s uses shuffle s. The team version fixes **which ten experts** are scored. The seed fixes **which of the five training shuffles** the router learned from. The seed already fixes the review order and the deference draws (section 5), so one seed number covers every random choice in a run.
   - **Retrained on the twins.** The router models are trained to predict the twins, by the framework's own procedure, including its search for settings, on training files built for the drawn teams by the framework's own script (section 3).
   - **The classifier's score** is its confidence in its own decision. The classifier gives each alert a score h between 0 and 1, as in policy 1, and confirms the alert when h is 0.5 or more. Its confidence is h when it confirms and 1 − h when it dismisses, so it is always at least 0.5. This is how the framework itself scores the model.
   - **Team-aware scores.** The router aims at the team's final decision; the trees show the result for each team. Two facts behind them:
     - For team B, the chance that B's final decision is right is 0.8 × the classifier's score + 0.2 × the expert's own score, because the router cannot know which reviewed alerts B defers on. This ranks the experts, and each expert against the classifier, exactly as the experts' own scores do, so B is routed on the experts' own scores. Computing the mix itself could create or break exact ties by rounding alone.
     - For team C, on an alert that meets team C's test, C's final decision does not depend on the expert, so a review cannot change it. Such alerts are counted as "team C test" alerts, not as equal scores (section 11).
4. **Routing: the framework's OvA rule, with an unlimited classifier.** The paper describes the rule as: "Deferral is done instance-wise to the expert/model that is most likely to be correct, until their work capacity is exhausted, at which point it chooses to defer to the second most likely to be correct, and so forth" (Paper p. 19). The trees apply it with the shared pool (item 1) and the unlimited classifier (item 2). The alerts are taken in the seed's random review order (policy 2 section 2, item 5).
   - **Equal scores** (the tie steps in the trees). Scores count as equal only when they are exactly equal, with no tolerance. A tolerance would send alerts away from the higher scorer, and which scores count as tied would depend on how the comparison is carried out. The framework does not fix how ties are broken. How many ties occur, and which step resolved each, is recorded (section 11).
5. **Final decision.** The team rules in the trees are policy 2's (policy 2 section 2.1). Team B uses the same deference draws as policy 2: one random number per alert and seed.
6. **No alert is left over.** Every alert is decided by the expert or the classifier it is routed to. Policy 2's rule for alerts beyond capacity, which confirms them without review, never applies.
7. **Routings per team.** Teams A and B share one routing (item 3); team C has its own. This sets the number of routings (section 5).
8. **The cost ratio does not change the routing.** The scores are fixed, because the router and the classifier were both trained once, at the cost ratio 0.057. The experts' decisions and the deference draws are fixed too. So, as in policy 2, each team instance is replayed once per capacity and seed, and the result is then costed at each cost ratio.

### 2.1 The teams' behaviour

**The three trees below are the master record of the teams' behaviour in policy 3.** Any other statement of that behaviour, in this design or in any other artefact, that contradicts them is wrong.

In all three trees: the **expert's own score** is the router's estimate that this expert's own decision is right; the classifier's score is h if it confirms and 1 − h if it dismisses; the pool holds K alerts shared by the ten experts; the classifier has no limit; an expert's **slot** is its position in the team, numbered as in policy 2 (Sources, "Plain terms").

#### Team A: behaviour diagram

```
                        ┌──────────────────────────────┐
                        │ Next alert, in the seed's    │
                        │ order                        │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │ Does the experts' pool still │
                        │ have room? (fewer than K     │
                        │ alerts reviewed so far)      │
                        └───────┬──────────────┬───────┘
                              no│              │yes
                                │   ┌──────────▼──────────────────┐
                                │   │ Pick the best expert:       │
                                │   │ highest >>own score<<       │
                                │   │ (tie: fewest alerts so far, │
                                │   │  then lower slot)           │
                                │   └──────────┬──────────────────┘
                                │              │
                                │   ┌──────────▼──────────────────┐
                                │   │ Is the best expert's score  │
                                │   │ STRICTLY higher than the    │
                                │   │ classifier's?               │
                                │   │ (equal → classifier)        │
                                │   └──────┬───────────────┬──────┘
                                │        no│               │yes
                                ▼          ▼               ▼
                   ┌────────────────────────────┐  ┌──────────────────────────┐
                   │ CLASSIFIER decides         │  │ EXPERT reviews           │
                   │ Pool unchanged             │  │ Pool down by one         │
                   └─────────────┬──────────────┘  └────────────┬─────────────┘
                                 │                              │
                   ┌─────────────▼──────────────┐  ┌────────────▼─────────────┐
                   │ Classifier's score h       │  │ Expert's own decision    │
                   │ ≥ 0.5?                     │  │ (team A's rule)          │
                   └──────┬──────────────┬──────┘  └──────┬────────────┬──────┘
                       yes│              │no         confirms│            │dismisses
                          ▼              ▼                   ▼            ▼
                   ┌────────────┐ ┌────────────┐   ┌────────────┐ ┌────────────┐
                   │ Alert      │ │ Alert      │   │ Alert      │ │ Alert      │
                   │ confirmed  │ │ dismissed  │   │ confirmed  │ │ dismissed  │
                   │ Application│ │ Application│   │ Application│ │ Application│
                   │ REJECTED   │ │ ACCEPTED   │   │ REJECTED   │ │ ACCEPTED   │
                   └────────────┘ └────────────┘   └────────────┘ └────────────┘
```

#### Team B: behaviour diagram

```
                        ┌──────────────────────────────┐
                        │ Next alert, in the seed's    │
                        │ order                        │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │ Does the experts' pool still │
                        │ have room?                   │
                        └───────┬──────────────┬───────┘
                              no│              │yes
                                │   ┌──────────▼──────────────────┐
                                │   │ Pick the best expert:       │
                                │   │ highest own score           │
                                │   │ (tie: fewest alerts so far, │
                                │   │  then lower slot)           │
                                │   └──────────┬──────────────────┘
                                │   ┌──────────▼───────────────────┐
                                │   │ Best expert's score STRICTLY │
                                │   │ higher than the classifier's?│
                                │   └──────┬───────────────┬───────┘
                                │        no│               │yes
                                ▼          ▼               ▼
              ┌────────────────────────────┐   ┌──────────────────────────────┐
              │ CLASSIFIER decides         │   │ EXPERT reviews               │
              │ Pool unchanged             │   │ Pool down by one             │
              └─────────────┬──────────────┘   └──────────────┬───────────────┘
                            │                  ┌──────────────▼───────────────┐
              ┌─────────────▼──────────────┐   │ Do the expert and the        │
              │ h ≥ 0.5?                   │   │ classifier agree?            │
              └──────┬──────────────┬──────┘   └──────┬────────────────┬──────┘
                  yes│              │no            yes│                │no
                     ▼              ▼                 ▼                ▼
              ┌────────────┐ ┌────────────┐  ┌────────────────┐ ┌─────────────────────┐
              │ Alert      │ │ Alert      │  │ That shared    │ │ This alert's        │
              │ confirmed  │ │ dismissed  │  │ decision       │ │ deference draw      │
              │ Application│ │ Application│  │ (confirm →     │ │ below 0.8?          │
              │ REJECTED   │ │ ACCEPTED   │  │  REJECTED;     │ │ (about 4 in 5)      │
              └────────────┘ └────────────┘  │  dismiss →     │ └────┬───────────┬────┘
                                             │  ACCEPTED)     │   yes│           │no
                                             └────────────────┘      ▼           ▼
                                                           ┌──────────────┐ ┌──────────────┐
                                                           │ CLASSIFIER'S │ │ EXPERT'S own │
                                                           │ decision     │ │ decision     │
                                                           │ stands       │ │ stands       │
                                                           └──────────────┘ └──────────────┘
```

Team B, where the expert and the classifier disagree:

| Expert | Classifier | Draw below 0.8 (about 4 in 5) | Draw 0.8 or above (about 1 in 5) |
|---|---|---|---|
| Confirms | Dismisses | Alert dismissed, application **accepted** | Alert confirmed, application **rejected** |
| Dismisses | Confirms | Alert confirmed, application **rejected** | Alert dismissed, application **accepted** |

The deference draw is fixed before routing, but the routing never looks at it.

#### Team C: behaviour diagram

```
                        ┌──────────────────────────────┐
                        │ Next alert, in the seed's     │
                        │ order                         │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │ Applicant aged 50 or over     │
                        │ AND classifier's h ≥ 0.5      │
                        │ (classifier would confirm)?   │
                        └───────┬──────────────┬───────┘
                             yes│              │no
                                │   ┌──────────▼──────────────────┐
                                │   │ Does the experts' pool still │
                                │   │ have room?                   │
                                │   └──────┬───────────────┬──────┘
                                │        no│               │yes
                                │          │   ┌───────────▼─────────────────┐
                                │          │   │ Pick the best expert:        │
                                │          │   │ highest own score            │
                                │          │   │ (tie: fewest alerts so far,  │
                                │          │   │  then lower slot)            │
                                │          │   └───────────┬─────────────────┘
                                │          │   ┌───────────▼─────────────────┐
                                │          │   │ Best expert's score STRICTLY │
                                │          │   │ higher than the classifier's?│
                                │          │   └──────┬───────────────┬──────┘
                                │          │        no│               │yes
                                ▼          ▼          ▼               ▼
              ┌────────────────────┐ ┌────────────────────────┐ ┌──────────────────────┐
              │ CLASSIFIER decides │ │ CLASSIFIER decides     │ │ EXPERT reviews       │
              │ Pool unchanged     │ │ Pool unchanged         │ │ Pool down by one     │
              └─────────┬──────────┘ └───────────┬────────────┘ └──────────┬───────────┘
                        │                ┌───────▼────────┐     ┌──────────▼───────────┐
                        │                │ h ≥ 0.5?       │     │ Expert's own decision│
                        │                └──┬──────────┬──┘     │ (the bias rule can't │
                        │                yes│          │no      │  fire here)          │
                        ▼                   ▼          ▼        └───┬─────────────┬────┘
              ┌────────────────┐  ┌────────────┐ ┌────────────┐ confirms│     │dismisses
              │ Alert confirmed│  │ Alert      │ │ Alert      │         ▼     ▼
              │ Application    │  │ confirmed  │ │ dismissed  │ ┌──────────┐ ┌──────────┐
              │ REJECTED       │  │ Application│ │ Application│ │ Alert    │ │ Alert    │
              └────────────────┘  │ REJECTED   │ │ ACCEPTED   │ │ confirmed│ │ dismissed│
                                  └────────────┘ └────────────┘ │ App.     │ │ App.     │
                                                                │ REJECTED │ │ ACCEPTED │
                                                                └──────────┘ └──────────┘
```

### 2.2 What follows from the trees (arithmetic, not results)
- **At capacity 0, policy 3 is policy 1.** Every alert goes to the classifier, for every team.
- **Only reviewed alerts make a difference against policy 1.** An alert routed to the classifier gets exactly policy 1's decision, so it contributes nothing to the difference between policy 3 and policy 1.
- **Fewer than K alerts may be reviewed.** An expert takes an alert only if it scores strictly higher than the classifier. How many alerts are reviewed is an outcome (section 6, load).
- **The reviewed alerts are nested across capacities.** Call an alert *eligible* when the best expert's score is strictly above the classifier's and, for team C, team C's test is false. Whether an alert is eligible depends only on its scores and the team, not on K and not on earlier alerts. Which expert takes an eligible alert depends only on the eligible alerts before it in the order (through the equal-scores rule). Therefore, within one team routing (A and B together, or C), version and seed:
  - the alerts reviewed are the first K eligible alerts in the seed's order, or all of them if there are fewer than K;
  - the routing at a lower capacity is the routing at a higher capacity cut off after its first K eligible alerts, with the same expert on every reviewed alert;
  - once K reaches the number of eligible alerts, the routing no longer changes with capacity, so neither do the results. The load (section 6) is then the number of eligible alerts divided by K.

  This follows from the rules; it is not a result. It holds within each routing only: team C's eligible alerts are team A's without the alerts that meet team C's test, so C and A do not review the same alerts at the same capacity. It is checked (check P3-C1, T10, section 8.1).
- **Team B moves only a fifth of the way away from automation.** A and B have the same routing. Where B's tree ends in the classifier's decision on a reviewed alert, B neither gains nor loses against policy 1 on that alert. Where it ends in the expert's own decision, B gains or loses exactly what A does on that alert. So, on expected loss and on accepted frauds, B's difference from policy 1 comes only from the alerts where it keeps the expert's decision against the classifier's. It is about a fifth of A's difference on the same alerts. This holds alert by alert, by construction. It does not carry over directly to the age gap, which compares two rates rather than adding up alerts.
- **Team C against team A.** On reviewed alerts, C decides as A would, because the bias rule cannot fire after review. C differs from A in two ways: alerts that meet team C's test are always confirmed (A may send them to an expert who dismisses them); and C's pool, spared those alerts, reaches alerts A's pool may not.
- **Policy 3 and policy 2 differ in two ways at once, at the same capacity.** First, which alerts are reviewed, how many (up to K in policy 3, exactly K in policy 2) and by which expert. Second, what happens to the alerts not reviewed: in policy 3 the classifier decides them; in policy 2 they are confirmed without review. The split of section 6 shows the two parts (limit 10).
- **What the scores mean** (arithmetic from the training weights, not from a source).
  - The router and the classifier were trained the same way: a missed fraud counts 1, a wrongly rejected legitimate application counts 0.057 (Paper p. 20).
  - If both were accurate, the decision-maker with the highest score on an alert would be the one with the lowest expected cost on that alert at the cost ratio 0.057. Comparing an expert's score with the classifier's would then compare their expected costs on that alert.
  - Neither is fully accurate. The classifier's score is deliberately shifted towards fraud by a starting offset added to every score (Paper p. 20; Table 4, p. 23: "initial score" 1.982). How well the router trained here ranks the twins' correctness is this study's own measurement: on month 6 (check P3-G (c)), read as limit 11 states, and on month 7, reported in section 6.
  - The routing is therefore an imperfect, fixed rule, tuned to 0.057.

## 3. What is used

**The router.** Our experts are the twins, regenerated with the age weight set to 0 and fitted on months 3 to 6, which also changes each expert's balance between the two kinds of error (policy 2 design, limit 5). So the router is retrained to predict the twins, in four steps.

1. **Training files.** 25 training set-ups, one per drawn team r and shuffle k, are built with the framework's own script and configuration, with the ten experts of training team r fixed to drawn team r. Each set-up consists of three files: the training cases, the batches (which batch each alert belongs to) and the members' capacities per batch (Paper p. 11), 75 files in all. The batch seeds, the shares and the dealing are the framework's. The training-cases file holds every alert of file months 3 to 6, with its case details, label and month. Check P3-G (g) confirms the membership, and check P3-G (e2) confirms that a second build gives identical files.
2. **Training.** One model per twin of drawn team r, for each of the 25 set-ups: 250 models, trained in this order: first the 10 models of drawn team 1, shuffle 1; then their second training (step 3); then the other 240. Training cases: the alerts of file months 3 to 5 that the file gives that expert. Case details and weights (0.057 and 1) are those of the framework's procedure, and the target is whether the twin's decision was correct. Settings: chosen by the framework's own search, unchanged: 120 trials, with the search's seed 42, the model's seed 42 and 10 threads, selecting the lowest weighted log-loss on file month 6. Month 6 therefore selects the settings, a choice taken from the framework's search procedure, and check P3-G (c) on month 6 is optimistic (limit 2). The model kept for each twin is the one the search saved at its selected trial. It is not fitted again.
3. **Reproducibility.** The 10 models of drawn team 1, shuffle 1, are trained first, then a second time exactly as the first, including the search, before the other 240 are trained. The two trainings must be identical (check P3-G (f)). The first training's 10 models are the ones used for routing.
4. **Month-7 predictions** are made after the router training (steps 2 and 3), as the first step of the policy 3 run, stored as 25 tables, one per drawn team and shuffle, each covering the 4,457 month-7 alerts, with one column per twin of the team plus the classifier's score. Check P3-G (b) checks the file before any replay uses it.

Size: section 12. **Disclosed:** these are the only models the project trains for use in the reported results (limit 2), against the project outline's aim to "minimise the resources spent on re-training of the existing models" (Method); they use the framework's own search for each model, because the drawn teams have no shipped settings.

**The router shipped with the framework** is not used for routing.

| Element | What |
|---|---|
| Alerts, labels, age | As policy 2 section 3 |
| Expert decisions | The unbiased twins, made a second time, where they must come out identical (policy 2 check P2-G (e)), as policy 2 section 3 |
| Team versions, review order, deference draws | As policy 2 sections 2 and 4. Policy 2's dealing is not used. Team membership: the draw record (policy 2 check P2-M) |
| Router predictions | The trained router's month-7 predictions (step 4) |
| The classifier's score h | Recomputed on month 7 exactly as in policy 1 design section 4, step 1. Checked against policy 1's decision on every alert: policy 1 confirms exactly when h is 0.5 or more |
| Policy 1 and policy 2 per-alert results | Policy 1's decision on each alert; policy 2's per-alert results averaged over the seeds, which feed comparisons 4 to 6; for the access to a reviewer by age group (section 6), the applicant's age group from policy 1's per-alert export, and policy 2's position of each alert in the review order, per team instance and seed |

## 4. The three teams

How each team decides an alert is set out in [section 2.1](#21-the-teams-behaviour), with one diagram per team: [team A](#team-a-behaviour-diagram), [team B](#team-b-behaviour-diagram) and [team C](#team-c-behaviour-diagram).

As policy 2 section 4, unchanged: the same twins in the same five versions, the same team rules, the same target cost for the experts. In policy 3, how routing and the team rules combine is specified by the trees of section 2.1.

## 5. The sweep

As policy 2 section 5:
- **Capacities:** 0 to 1 in steps of 0.05, plus 10/11, the share the benchmark gives its experts (policy 2 section 5); 22 values in all. In policy 3 each is a ceiling on the alerts the experts review.
- **Cost ratios:** 0.035, 0.0537, 0.057 and 0.171.
- **Seeds:** 1 to 5. In policy 3, a seed fixes the review order, team B's deference draws, and which of the router's five training shuffles is used.

**Realistic range** (as policy 2): capacities 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 10/11, 0.95 and 1. Team A is the control at capacity 1. Teams B and C are judged across the range. Capacity 0.75 is the level for the comparisons with naive review.

**Why the realistic range decides.** At capacity 0 policy 3 is policy 1 (section 2.2), so "no difference" there is certain and says nothing. The question is what happens at realistic capacities.

**Size.** 22 capacities × 5 seeds × 5 versions = 550 routings shared by A and B, and 550 for C: 1,100 routings. They give 1,650 team replays. Each replay is costed at 4 cost ratios, which gives 6,600 results (cells).

## 6. What is measured

As policy 2 section 6: the three measures; seeds averaged before resampling; the ratio indicators; and indicators that are not defined at capacity 0. Where policy 3 differs from policy 2 is below. The load, the number of eligible alerts, the workload per expert, criterion 1 as it turns out, the router's ranking quality and the split against policy 2 are descriptive, and so is the access to a reviewer by age group.

| Measure | In policy 3 |
|---|---|
| **Split of the difference against policy 1** | Not needed. The part from the alerts routed to the classifier is 0 by construction (section 2.2). It is checked (P3-C1, T6), not reported as a finding |
| **Split of the difference against policy 2** | Two parts, each policy 3's result minus policy 2's on the same alerts. **Classifier part:** the alerts policy 3 sends to the classifier. **Reviewed part:** the alerts policy 3 sends to an expert. The two parts add up to the whole difference in every seed. Descriptive |
| **Override rate, loss avoided per review, subgroup disparity on reviewed alerts** | As policy 2, on the alerts routed to an expert. The denominators are the alerts actually reviewed |
| **Load** (defined differently from policy 2) | Alerts reviewed ÷ K, per team, version, capacity and seed. In policy 3 it is a finding, not 1 by construction: K is a ceiling |
| **Workload per expert** (policy 3 only) | For each version, capacity and seed: the number of alerts routed to each expert and to the classifier. The pool is shared, so the workload between experts can be very uneven |
| **Criterion 1, as it turns out** (policy 3 only) | On reviewed alerts: the share where the expert is right and policy 1 is wrong; and the share where the expert is wrong and policy 1 is right. (As the router sees it, criterion 1 holds by construction and is checked, P3-C1, T9) |
| **Router ranking quality** (policy 3 only; month 7) | For each expert, on all 4,457 alerts: how well its own score separates the alerts it decides correctly from those it gets wrong. It is the area under the ROC curve with each alert weighted by its fraud label (0.057 if legitimate, 1 if fraud), computed exactly, without resampling (Sources, "Plain terms"); 0.5 is chance and 1 is perfect. Shown beside the month-6 figures of P3-G (c). Descriptive |

**Policy 2's age-gap label in comparisons 5 and 6.** Policy 2's age-gap property (policy 2 section 6) does not apply to policy 3's own figures: in policy 3 no alert is confirmed for lack of capacity. It does apply to the policy 2 side of comparisons 5 and 6, where policy 2 confirms every alert beyond capacity. There, wherever the point estimate of policy 2's absolute age gap (mean of the five versions) is closer to zero than policy 3's, while policy 2's overall false rejection rate is higher, the age-gap result carries policy 2's label "gap narrowed by rejecting more applicants in both groups". Both policies' overall false rejection rates are shown beside the age-gap result of comparisons 5 and 6, per version and for the mean of the five. The verdict is unchanged. Comparison 4, at capacity 1, has no alert beyond capacity and is unaffected.

**Access to a reviewer by age group** (policy 3, with policy 2 beside it). Descriptive.
- **Groups.** The 4,457 alerts fall into four groups: the applicant is aged 50 or over, or under 50; and the classifier would confirm the alert (policy 1 rejects the application), or would dismiss it. The groups depend only on the alert, so they are the same for every team, version, seed and capacity.
- **Sent to a reviewer.** In policy 3, an alert is sent to a reviewer when its decision-maker is one of the team's ten experts, not the classifier. In policy 2, an alert is sent to a reviewer when it is among the first K alerts of the seed's review order, the rule the policy 2 replay uses for the decision (Sources, "Plain terms").
- **Counts.** For each policy, team, version, seed and capacity, and for each group: the number of alerts, and the number sent to a reviewer.
- **Shares.** In each age group, the share of alerts sent to a reviewer: (i) overall; (ii) among the alerts the classifier would confirm; (iii) among those it would dismiss. For each of (i) to (iii), the difference between the two age groups: the share for those aged 50 or over minus the share for those under 50, in percentage points.
- **Policy 2 beside it.** The same counts, shares and differences for policy 2, at the same team, version, seed and capacity, taken from policy 2's per-case export.
- **Reported as point figures:** per version, the mean over the five seeds, with the range over seeds; and the mean of the five versions. No interval and no verdict; nothing is added to the bootstrap. The number of alerts in each group is the same in every seed, so the mean over seeds of a share equals the share of the five seeds pooled.
- **Not defined.** If a group holds no alert, its shares, and every difference that uses them, are "not defined", shown as such and never as 0.
- **From the trees and the rules (not results).** In P3-T9 and P3-F9 these are labelled "by construction", not presented as findings:
  - **Policy 3, team C:** no alert of an applicant aged 50 or over that the classifier would confirm is sent to a reviewer, at any version, seed or capacity; that cell is 0. Such alerts meet team C's test and go to the classifier (section 2.1). Team C's test is applied with the same classifier score as policy 1's decision (Sources, "Plain terms"), so the 0 holds exactly. A count other than 0 is a failed check P3-C1 T5, not a result.
  - **Policy 3, team B:** every figure equals team A's, at every version, seed and capacity, because A and B share one routing (section 2, item 7; check P3-C1 T4).
  - **Policy 2:** within a seed, the figures are the same for all three teams and all five versions, because they share the review order (policy 2 section 2, item 4); policy 2's lines are therefore the same in every panel of P3-F9. Policy 2's team C cell for applicants aged 50 or over whose alert the classifier would confirm is not 0 at any capacity above 0: those alerts are reviewed while capacity lasts, and team C's rule then confirms them (policy 2 section 2.1). At capacity 1 every policy 2 share is 1. Between capacities 0 and 1, each group's share differs from K ÷ 4,457 only through the random order.
  - **Both policies, capacity 0:** every share is 0.
  - **Everything else** in policy 3 (teams A and B; team C's other cells): no direction is fixed by the rules. These figures are results.
- **What it supports:** statements of the form "under this routing, x% of the applicants aged 50 or over whose alert the classifier would confirm were sent to a reviewer, against y% of those under 50", beside policy 2 at the same capacity. **What it does not support:** any verdict; any statement on whether the routing is lawful; any cause for the figures of teams A and B. It is not among the 66 deciding results and enters no rule of section 8.3.

## 7. Comparison method

As in policy 2 section 7. Version r of policy 3 is compared with version r of policy 2, which has the same experts. The only difference is the width of the deciding intervals:

- **Interval level.** 66 results decide (section 8.2). If each used an ordinary 95% interval, some would show a difference by chance alone. Each deciding interval is therefore widened so that, across all 66 together, the chance of a false finding stays at about 5% (a Bonferroni adjustment).
  - Each deciding interval covers 1 − 0.05/66 of the resamples, about 99.924%.
  - Its ends are at the percentiles 2.5/66 % and 100 − 2.5/66 %, that is 0.037879% and 99.962121% to six decimals, computed at full precision. That leaves about 19 resamples beyond each end.
  - The 66 are adjusted among themselves, not together with policy 2's 61.
  - Every other interval is an ordinary 95% interval and is descriptive.

## 8. Checks and decision rules

Outcome words, fixed: "supported", "not supported", "not testable". Every rule is applied as written; the full table is kept and reported.

### 8.1 Checks

Everything the study uses is checked.

**P3-0. Earlier checks first.**
- **The router checks P3-G (c), (d), (e2) and (g)** require policy 2's checks P2-G (b) and P2-M (0) to (4) to have passed.
- **The router training and P3-G (f)** require policy 2's check P2-G (e), and P3-G (e2) and (g), to have passed.
- **The routing, the replay and every policy 3 figure** require policy 2's checks P2-G (b) and (e), P2-M in full (items (0) to (5)) and P2-C1, and checks P3-G (b), (c), (d), (e2), (f) and (g), to have passed. If not, none of these is evaluated until they have.

**P3-G. Router files.**
- **(b) The project's month-7 router prediction file.** Straight after the month-7 router predictions are made (section 3, step 4), and before any replay uses them:
  - **Structure:** 25 tables, one for each team r (1 to 5) and shuffle s (1 to 5); each covers exactly the 4,457 month-7 alerts; each has exactly one column per twin of team r, the same ten as policy 2 uses, plus the classifier's score.
  - **Range:** every score lies between 0 and 1.
  - **Classifier column:** in every table, the classifier's score equals its confidence as recomputed in section 3 (h or 1 − h, whichever is larger), within the tolerance set out in Sources, "Plain terms".
  - **Column mapping:** each twin column i of table (r, s) equals, within the same tolerance, a fresh prediction from the trained model file of team r, shuffle s, twin i, loaded by its location.
  - The largest difference found is reported for each comparison. Pass rule: every item holds in 25 of 25 tables.
- **(c) How well the router ranks the twins, months 3 to 6 only.** Run on the 250 models trained on the drawn teams' files, before any month-7 prediction.
  - The retrained router models predict on file month 6.
  - For each expert and shuffle, ranking quality is measured as in section 6, against whether the twin was actually correct: weighted by the alert's fraud label (0.057 if legitimate, 1 if fraud), computed exactly, without resampling.
  - Two independent routes compute it and must agree within 1e-9 (Sources, "Plain terms").
  - **Inputs**, in every computation of ranking quality for the drawn teams (month 6 in this check, and month 7): the weights are asserted to be exactly 0.057 on every legitimate alert and 1 on every fraud; the twin's correctness is taken from the twin columns under the pairing recorded in P3-G (d); a negative control with two twin columns swapped must change the result. The two routes share these inputs, so their agreement does not test them.
  - Then the average for each team version is reported.
  - Month 6 selected each model's settings (section 3, step 2), so the figure is optimistic.
  - Its month-6 result is carried into limit 11 by the rule stated there.
- **(d) Retrained router.** For each of the 250 retrained models:
  - **Settings:** exactly the settings of the first trial with the lowest weighted log-loss on file month 6 (the strict selection keeps the first of tied trials). They are read from the project's search record: for each trial, its number, settings and weighted log-loss, as the framework's search computes it. The settings are checked one by one against the model kept, with 10 threads. Two cross-checks are made: (i) the settings in the search record equal the framework's own record of the settings for that model, trial by trial in order, 120 of 120; (ii) the model kept is the one the framework saves at the selected trial. Any difference is a failure.
  - **Alerts:** it was fitted on exactly the alerts of file months 3 to 5 that the drawn team's training-cases file gives that expert in that shuffle. Three conditions, each for every model:
    - (i) the number of training rows equals the number of rows that the training-cases file gives that expert in file months 3 to 5;
    - (ii) the case identifiers are the same;
    - (iii) the retrained model's own record of its training rows (the row count at the root of its first tree) equals that number, so the check is tied to the model used for routing.
    - The reference for (i) and (ii) is the training-cases file itself, after its checksum is confirmed equal to the one recorded when it was created, read a second time apart from the training step, and selected by a route that shares no selection code with the training step. Selection code is the code that picks the rows (by expert and by month); the library that decodes the file is not selection code.
  - **Target:** the training target of each model equals, alert by alert and exactly, whether twin i's decision equals the fraud label in the alerts file. The reference is recomputed from those two files, not taken from the training step.
  - **Twin pairing:** each twin column i is the twin of stored expert i, shown by an independent route: twin i is generated from the same expert seed as stored expert i, for 50 of 50 experts, exactly. A negative control that swaps two experts' seeds must fail.
  - **Pass rule:** settings, alerts and target hold for 250 of 250 models, and the pairing for 50 of 50 experts, with no tolerance. Run on the 250 models trained for the drawn teams.
- **(e2) The drawn teams' training files can be reproduced; before any model is trained.** The 25 set-ups are built a second time, in the same way, with the same configuration and seeds, into a separate folder. Pass: the checksum of each of the 75 files equals that of the first build, 75 of 75. The second copy is deleted after the comparison. Nothing from month 7 is written.
- **(f) Router training reproduces.** The 10 models of drawn team 1, shuffle 1, are trained first, then a second time exactly as the first, including the search, before the other 240 are trained. The first training's 10 models are the ones used for routing: their checksums are recorded, and the training of the other 240 does not overwrite them. If they are trained again anyway, the copies used for routing are compared with the first training by the same pass rule, and any difference is a failure of (f). Pass: for each of the 10 models, the checksum of the model equals the first training's, and every trial in the search record has the same settings and the same weighted log-loss (compared exactly, as stored), 10 of 10.
- **(g) Membership of the training files.** For each of the 25 set-ups (drawn team r, shuffle k): (1) the experts in the training-cases file's assignment are exactly the ten stored experts paired with drawn team r's twins, and each has at least one alert of file months 3 to 5; (2) every alert of file months 3 to 6 is in the training-cases file exactly once, with the same case details, labels and month as the alerts file; (3) the set-up's batches equal those of a build of the same shuffle k by the framework's script with its own membership draw, because batches depend only on the shuffle seed. This shows that fixing the membership changes only the membership; (4) in every batch, the members' capacities add up to the batch size. Pass: 25 of 25 set-ups.
- **If it fails.**
  - If (b) or (d) fails, no policy 3 figure is used.
  - If (e2) fails, none of the drawn teams' training files is used, and no router model is trained on one. There is no fallback.
  - If (f) or (g) fails, no policy 3 figure is used.
  - For (c): if the average for the twins in any team version is 0.5 or below, meaning no better than chance, no policy 3 figure is used until it is resolved. If the two routes disagree beyond 1e-9, the check fails.

**P3-C1. The replay is correct.** For each team, version, capacity and seed, all of the following hold exactly:
- **T1.** Every alert is routed to exactly one decision-maker.
- **T2.** The experts together receive at most K alerts, and the classifier receives all the others.
- **T3.** Re-running the routing from the recorded scores, order and K gives the same result as the export. Every alert went where the team's tree in section 2.1 sends it, with equal scores resolved as in section 2, item 4.
- **T4.** Teams A and B have the same routing (section 2, item 7).
- **T5.** On alerts routed to the classifier, every team's final decision equals policy 1's. On reviewed alerts, the final decision is the outcome of the team's tree (section 2.1). For team C, no reviewed alert is from an applicant aged 50 or over whose alert the classifier would confirm.
- **T6.** On the alerts routed to the classifier, the difference between policy 3 and policy 1 is 0 on every measure. At capacity 0, policy 3 equals policy 1 on every alert.
- **T7.** Policy 1 confirms an alert exactly when h is 0.5 or more, on every alert.
- **T8.** As policy 2's T8: the same set of alerts, labels and ages.
- **T9.** Criterion 1 as the router sees it: on every reviewed alert, the reviewing expert's own score is strictly higher than the classifier's score. For teams A and C this is the team-aware score itself, because team C's test alerts are never reviewed. For team B it is equivalent to the team-aware score by the algebra in Sources, "Plain terms"; the mixed score is not computed, because rounding could make a correctly routed alert fail the check.
- **T10.** Nesting (section 2.2): for each team routing, version and seed, and each pair of capacities, the reviewed alerts at the lower capacity are the first ones reviewed at the higher capacity, in the seed's order, each with the same expert; and the number reviewed at each capacity is the smaller of K and the number of eligible alerts.

If any fails, no policy 3 figure is used until it is explained, as in policy 2.

**P3-V. The verdicts are recomputed.** As policy 2's P2-V, after the bootstrap, from the exports:
- every verdict word recomputed from the exported interval ends and the 1e-9 zero threshold;
- the five-version outcome of every deciding result recomputed from the exported verdicts of the five versions and of their mean;
- policy 2's age-gap label on the policy 2 side of comparisons 5 and 6 (section 6) recomputed from the exported age gaps and overall false rejection rates;
- for a fixed sample, each interval recomputed by policy 2's second, plain route: comparison 1 on all three measures; comparison 5 on the age gap; comparison 6 on expected loss; each with its five versions and their mean.

Pass rule: the first three items exactly equal to the exports; every recomputed interval end within |x − y| ≤ 1e-9 × max(1, |y|), where y is the exported value. If it fails, no verdict of policy 3 is used.

### 8.2 Main comparisons

All at the cost ratio 0.057. Only these 66 results decide. Each is judged on its own measure; measures are not combined.

| Comparison | Expected loss | Regulatory exposure (accepted frauds) | Fairness exposure (absolute age gap) | Deciding results |
|---|---|---|---|---|
| **1.** Team A at capacity 1, policy 3 against policy 1 | decides | decides | decides | 3 |
| **2.** Team B, policy 3 against policy 1, at each of the 9 realistic capacities | decides | decides | decides | 27 |
| **3.** Team C, policy 3 against policy 1, at each of the 9 realistic capacities | decides | decides | decides | 27 |
| **4.** Team A at capacity 1, policy 3 against policy 2 | decides | decides | decides | 3 |
| **5.** Team B at capacity 0.75, policy 3 against policy 2 | decides | decides | decides | 3 |
| **6.** Team C at capacity 0.75, policy 3 against policy 2 | decides | decides | decides | 3 |
| **Total** | | | | **66** |

For comparisons 2 and 3, the 9 verdicts per measure are also summarised as a boundary within the realistic range, as in policy 2 section 8.2. Descriptive only: policy 3 against policy 2 at the other realistic capacities, and teams B and C against team A within policy 3.

**What each comparison isolates** (from the rules in section 2):
- **Comparisons 1 to 3** come only from the reviewed alerts.
- **Comparison 4**, at capacity 1: in policy 2 every alert is reviewed, by an expert dealt at random; in policy 3 an alert is reviewed only where the best expert outscores the classifier, and the classifier decides the rest. So it measures the routing as a whole: whether an alert is reviewed, and by whom. The split (section 6) and the load show each part.
- **Comparisons 5 and 6** add a third effect: in policy 2 the 1,115 alerts beyond capacity are confirmed without review; in policy 3 every alert not reviewed is decided by the classifier. Their split shows each part.

**Expected for comparisons 5 and 6** (point value only; from the rules and, for expected loss, from policy 1's results; not from results of policies 2 or 3). On the alerts that policy 2 confirms without review at capacity 0.75:
- **Accepted frauds:** policy 2 accepts no fraud on those alerts, so policy 3 accepts as many or more there. This part favours policy 2 by construction.
- **Expected loss:** policy 2 costs 0.057 for each legitimate alert there. This part is expected to favour policy 3 in point value: over the month, at 0.057, policy 1's error counts give the classifier a cost of about 204.0 against 213.5 for confirming every alert (policy 2 rule P2-L), and the experts are built to a lower target cost (policy 2 section 4). Nothing is claimed about its interval.

To make these checkable, one descriptive point figure is reported for each of teams B and C at capacity 0.75, per version and for the mean of the five: policy 3's result minus policy 2's on the alerts policy 2 confirms without review, computed per seed and then averaged, on expected loss at 0.057 and on accepted frauds. No interval and no verdict (P3-T8).

### 8.3 Decision rules

| Id | Rule, checkable from the tables | What it supports | What it does not support |
|---|---|---|---|
| **P3-R0** Control | Comparison 1: one verdict per measure | "With capacity for every alert, a standard team with analyst-aware routing beats / does worse than / is not shown to differ from automation on the measure" | Anything about real reviewers or a better router |
| **P3-R1** Refutation clause 1 (strict reading) | Applied per measure, to the 57 deciding results of comparisons 1 to 3.<br>• **Clause met, hypothesis refuted on the measure,** if any one of them is not "beats". That is, some team, at some realistic capacity (team A: at capacity 1), does not outperform automation.<br>• **Clause not met** if all of them are "beats".<br>The results that are not "beats" are listed by team and capacity, with their verdict. Reported per measure, never combined.<br>*Example (invented, not results):* "On expected loss, analyst-aware deferral beats automation for teams A and C at every realistic capacity, but not for team B at 0.65 and 0.70 (no difference shown): refutation clause 1 is met on expected loss." | If not met on a measure: "analyst-aware deferral outperforms automation on the measure for every team at every realistic capacity". If met: as the project outline states, the benefit of human review is smaller and more conditional than assumed, with the failing teams and capacities named | That a better-trained router would or would not do better |
| **P3-R2** Against naive review | Applied per measure, to comparisons 4 to 6. "Supported on the measure" if policy 3 beats policy 2 in all three. Otherwise "not supported on the measure", with each comparison's verdict listed. Each result is shown with its split and the load (section 6). On the age gap, a result of comparison 5 or 6 that carries policy 2's label (section 6) is listed with that label | "At the capacity tested, analyst-aware deferral has lower risk on the measure than review-everything with the alerts beyond capacity confirmed unreviewed, for every team" | That it holds at every realistic capacity (descriptive only, P3-B); which part of the routing causes it, beyond the split (limit 10) |
| **P3-B** Capacity boundaries, cost ratio 0.057 | As policy 2's P2-B, for policy 3 against policy 1 and against policy 2, per team and measure. It finds the capacity at which policy 3 switches from doing worse to doing better (or the reverse), and gives a descriptive verdict at each capacity of the grid, with policy 2's rule for values at 0 and its examples. At the 9 realistic capacities, cells that are also deciding results carry the note "deciding verdict: see P3-T3" | As P2-B | As P2-B |
| **P3-X** Teams within policy 3 | Team B against team A, and team C against team A, at each capacity and per measure. Descriptive (95%). From section 2.2: B and A have the same routing; where B keeps the expert's decision, B and A are equal; where B defers, B gives up whatever A gains over automation on that alert (or avoids whatever A loses). C against A covers C's rule together with the routing's response to it | How much deference and the bias rule, with the routing's response, erode analyst-aware routing | A verdict |
| **P3-L** Low cost ratio | As policy 2's P2-L, for policy 3. At the cost ratio 0.035, a result that beats policy 1 on expected loss is also tested against "confirm every alert" (every application rejected) | As P2-L | As P2-L |
| **P3-U** Away from 0.057 | Policy 2's P2-U applies unchanged, including how results away from 0.057 are read and the statement that the baseline's disadvantage there is not measured. In addition, the router was also trained at 0.057 (section 2, item 8), so policy 3's routing is not re-tuned for other cost ratios either | — | A conclusion that holds across cost ratios |
| **P3-N** Chance count | As policy 2's P2-N, for policy 3's 15 team instances against policy 1. Among the descriptive 95% intervals, the number of "beats" and "does worse" is set against the number expected by chance alone. Capacity 0 is left out entirely, because there policy 3 is policy 1. Count: 21 capacities × 15 team instances × 6 results (expected loss at 4 cost ratios, accepted frauds, age gap) = 1,890 intervals | — | A verdict |

**From section 2.2** (arithmetic, not results). Team B's difference against policy 1 is about a fifth of team A's under the same routing. So B's results in comparison 2 are the most likely to be "no difference shown" at the widened interval level. Under the strict reading of P3-R1, a single such result meets refutation clause 1 on that measure.

## 9. Bias × capacity

- **Bias × capacity** is repeated for policy 3, as policy 2 section 9. Descriptive.
  - **The question:** does team C's bias compound or cancel when capacity is exceeded? Comparator: team A. Capacity exceeded: 0.75; adequate: 1.
  - **The measure:** for each of policy 2's three metrics (the signed age gap; the number of wrongly rejected applications of legitimate applicants aged 50 or over; expected loss at 0.057), the difference C − A at capacity 0.75 minus the difference C − A at capacity 1. Per version and for the average of the five, with a paired 95% interval. Read as policy 2: above 0, the bias compounds; below 0, it cancels in part; otherwise additive. The formula is in Sources, "Plain terms".
  - **None of the three signs is fixed by construction in policy 3,** so all three are findings, not checks. Facts from the rules (section 2.2), not results:
    - Within each team's routing the reviewed alerts are nested across capacities, as in policy 2.
    - In policy 2, C and A review the same alerts, so C − A is the sum of C's rule changes on them. In policy 3, C and A have different routings: C − A at a capacity is made of the alerts of applicants aged 50 or over that A sends to an expert and C confirms, plus the alerts C's pool reaches and A's does not. The second part has no fixed sign.
    - Once K reaches the number of eligible alerts of both routings, C − A is the first part alone.
  - **Policy 2's "expectation line" is not carried over.** It rests on the reviewed alerts being a random share of all alerts, which does not hold when the router picks them.
  - Team C against team A is also reported descriptively at every capacity (P3-X).

## 10. Results tables and figures

| Id | Content | Serves |
|---|---|---|
| P3-T1 | Routing, per team, version and seed, at capacities 1, 10/11, 0.75 and 0.65: the load; the number of eligible alerts (section 2.2); the number of alerts routed to each expert and to the classifier; for team C, the number of team C test alerts; the number of equal-score ties and which step resolved each; criterion 1 as it turns out; the router's ranking quality per expert on month 7, beside the month-6 figure of P3-G (c) | Sections 2 and 6 |
| P3-T2 | Checks P3-0, P3-G, P3-C1 and P3-V: pass or fail, item by item | Checks |
| P3-T3 | Verdict table of the 66 deciding results, as policy 2's P2-T3; for comparisons 5 and 6, both policies' overall false rejection rates beside the age-gap result, per version and for the mean, with policy 2's label where it applies (section 6); then the outcome of rules P3-R0 to P3-R2 per measure | All rules |
| P3-T4 | Capacity boundaries against policy 1 and against policy 2, as P2-T4 | P3-B |
| P3-T5 | Full sweep: every team instance, capacity and cost ratio; all measures, with 95% intervals and the range over seeds | Integrity (full sweep) |
| P3-T6 | Runtime and peak memory per run, by step (section 11, item 3) | Run record |
| P3-F1 | Expected-loss difference against capacity, at 0.057, one panel per team. Lines: policy 3 against policy 1, and policy 3 against policy 2. Each with five thin lines, one per version, plus their average, a 95% band, the realistic range shaded and the boundaries marked | P3-R0 to P3-R2, P3-B |
| P3-F2 | Same, for accepted frauds | Axis 2 |
| P3-F3 | Same, for the absolute age gap, with the overall rate of wrongly rejected applications on a second axis | Axis 3 |
| P3-F4 | Stacked bars of the difference between policy 3 and policy 2, split into its classifier and reviewed parts, by team and capacity | P3-R2 |
| P3-F5 | Monitoring indicators against capacity, per team: load, override rate, loss avoided per review, disparity on reviewed alerts, and criterion 1 as it turns out | Project outline indicators; this study's criterion 1 (section 1) |
| P3-F6 | Grid of cost ratio against capacity, showing the expected-loss verdict against policy 1, per team | P3-U |
| P3-F7 | Observed against expected numbers of "beats" and "does worse" | P3-N |
| P3-F8 | Forest plot of the 66 deciding results: each with its interval, the five versions as dots, and a line at zero | P3-T3 |
| P3-T7 | Bias × capacity: for each of the three metrics, the measure of section 9 per version and for the average, with its 95% interval and the reading (compounds / cancels in part / additive) | Section 9 |
| P3-T8 | Comparisons 5 and 6, on the alerts policy 2 confirms without review: the point figure of section 8.2, for teams B and C at capacity 0.75, per version and for the mean of the five, on expected loss at 0.057 and accepted frauds. No interval, no verdict | Section 8.2, the expectation for comparisons 5 and 6 |
| P3-T9 | Access to a reviewer by age group (section 6), at capacities 1, 10/11, 0.75 and 0.65, for each team: per version and for the mean of the five versions, the shares (i) overall, (ii) among alerts the classifier would confirm and (iii) among those it would dismiss, in each age group, with the counts behind each share and the difference between the age groups in percentage points; the range over seeds per version; policy 2's figures beside policy 3's. Team C's cell for applicants aged 50 or over whose alert the classifier would confirm is labelled "0 by construction"; team B's rows are labelled "identical to team A by construction". Policy 2's team C cell for applicants aged 50 or over whose alert the classifier would confirm is labelled "Reviewed, but the outcome is fixed by team C's rule: every such alert is confirmed under policies 1, 2 and 3 (policy 2 and policy 3 designs, section 2.1). The share is review capacity spent without effect on the decision: access to a reviewer, not a better outcome."; a note under team C's row (i) and its differences reads "Policy 2's overall share for applicants aged 50 or over includes these alerts." "Not defined" where a group is empty. Point figures, no interval, no verdict | Section 6, access by age |
| P3-F9 | Share of alerts sent to a reviewer against capacity, all 22 capacities. One panel per team, in two rows: (i) overall; (ii) among alerts the classifier would confirm. In each panel, one solid line per age group for policy 3 and one dashed line per age group for policy 2. Each line plots the mean of the five versions, each version first averaged over the five seeds; no band, since no interval is computed. Team C's line for applicants aged 50 or over in row (ii) is labelled "0 by construction"; in team C's panel, row (ii), policy 2's dashed line for applicants aged 50 or over is labelled "Policy 2: reviewed, outcome fixed by team C's rule; confirmed under policies 1, 2 and 3"; team B's panels are labelled "identical to team A by construction"; a note states that policy 2's dashed lines are the same in every panel. Descriptive | Section 6, access by age |

## 11. What every run records

As policy 2 section 11, plus:
1. **Router.**
   - The checksums of the 75 training files of the 25 drawn-team set-ups read (equal to those recorded at their creation), of every trained model and of the search record of each model (the project's trial record and the framework's own record of the settings, each with its checksum) and of the month-7 prediction file (taken when each is created); the LightGBM version; the thread count; and the runtime and peak memory of the router training.
   - For each seed and version: which router table was used (drawn team r, shuffle s).
   - Which stored expert's column stands for which twin.
   - The rule for equal scores and team C's routing test, as text and as implemented.
2. **Pool and routing.** For each team, version, capacity and seed: K; the number of eligible alerts; the number of alerts routed to each expert and to the classifier; for team C, the number of team C test alerts, counted apart from ties; the number of equal-score ties and which step resolved each; the checksum of the routing export.
3. **Runtime** and **peak memory** of each step of the run, as policy 2 section 11, item 5. The router's training files, the router training (with its search, where the search is run), the month-7 predictions, the routing with the replay, the bootstrap, the verdicts and the router's ranking quality are separate steps. The access-by-age counts (section 6) are recorded with the replay.
4. **Result.** Where the exports are (routing, per-alert master, cell results, seed-averaged bootstrap input, checks, access-by-age counts) and the verdict tables, as policy 2 section 11, item 4.
   - **Routing export:** one row per alert and routing, keyed by team routing (A and B together; C), version, seed, capacity and alert, with the alert's **decision-maker**: one of the team's ten experts, or the classifier. Every capacity is stored.
   - **Access-by-age counts export** (section 6), for policy 3 and policy 2: one row per policy, team, version, seed, capacity and group (age group × the classifier's decision), with the number of alerts and the number sent to a reviewer; its checksum is recorded. It is computed from the routing export, policy 2's per-case export and policy 1's per-alert export only, and changes none of them.

## 12. Size

- 1,100 routings of 4,457 alerts each: 550 shared by A and B, 550 for C; 1,650 team replays; 6,600 results.
- The bootstrap, at 50,000 resamples, produces the 66 deciding intervals (each with its five versions and their average) and the descriptive ones.
- Router: 250 models, each chosen by a search of 120 trials (30,000 fits), plus 10 models trained a second time for P3-G (f); 25 tables of month-7 predictions.

## 13. Limits

1. As policy 2 limits 1, 2, 3, 5, 6, 7, 9 and 10.
2. **The router and the twins.** The router is the framework's model, trained by the framework's own procedure, including its search for settings, on the twins' decisions, on training files built for the drawn teams. Its ranking quality for the twins is measured on month 6 (P3-G (c), optimistic, because month 6 selected the settings) and on month 7, and reported. These are the only models the project trains for use in the reported results. They are disclosed against the project outline's aim to minimise re-training (section 3).
3. **The results apply only to the router trained here.** Analyst-aware deferral is tested with this router, not with the best possible one. Its ranking quality is the measurement of limit 2: the month-6 figure is read as limit 11 states; the month-7 figure is reported in section 6.
4. **The routing uses team C's rule exactly**, as a router trained perfectly on C's final decisions would; the expert's own part of every score still comes from the router trained here (limit 3). It cannot know which alerts team B defers on.
5. **Capacity is a ceiling.** Criterion 1 holds as the router sees it, but can fail in fact, because the router's scores are estimates (limit 3). Criterion 3 is measured, not enforced. No cost of review is modelled, as in policy 2.
6. **Away from 0.057**, neither policy 1, the experts nor the router are re-tuned (P3-U).
7. **The order of the alerts matters.** The OvA rule takes alerts one at a time, so a different order gives a different routing; once the pool is used up, later alerts go to the classifier even where an expert would score higher. The order is policy 2's random order for each seed, so its effect is part of the spread over seeds. Above the capacity at which K reaches the number of eligible alerts, the order no longer changes which alerts are reviewed (section 2.2).
8. **Comparisons of policy 3 with policy 2 at realistic capacities other than 0.75 are descriptive.** The 66 deciding results are adjusted among themselves, not together with policy 2's 61, so the chance of at least one false finding across the two policies together is above 5%.
9. **Workload can be very uneven.** The shared pool lets the best-scoring experts take most alerts. This is reported (section 6), not limited.
10. **The routing's own effect is not separated.** Policy 3 against policy 2 mixes which alerts are reviewed, how many and by whom with how the alerts not reviewed are treated. The split of section 6 shows the classifier part and the reviewed part; it does not separate the router's choice from the treatment of the rest further.
11. **How well the retrained router ranks the twins.** If every version's average is above 0.5 (otherwise P3-G (c) applies): "On month 6, the retrained router ranks the twins' correctness above chance in every team version (P3-G (c))." Then, if n of the 250 models are at or below 0.5 and n > 0: "n of the 250 individual router models are at or below chance; results are read with this."

## Sources

| Short name | Source |
|---|---|
| Paper | Alves et al., "A benchmarking framework and dataset for learning to defer in human-AI decision-making", *Scientific Data* 12:506, 2025, cited by page. Paper months are file month + 1 |
| Project outline | The project outline, "Save the Human (in the loop): when does human oversight of AI actually reduce risk?", version 0.9, 18 September 2026 |
| Policy 1 design | [policy-1-design_v1.0.md](policy-1-design_v1.0.md) |
| Policy 2 design | [policy-2-design_v1.0.md](policy-2-design_v1.0.md) |

### Plain terms used in the body, and what they stand for

| Plain term | What it stands for |
|---|---|
| The classifier's confidence | max(h, 1 − h) |
| Training cases of an expert | Its rows in the training-cases file of drawn team r and shuffle k with file month 3 to 5 |
| Policy 1's decision | Coded 1 = alert confirmed (policy 2 design, section 2, item 6) |
| Final decision | D-Fnl (policy 2 design, section 2, item 6): 1 = alert confirmed |
| K | floor(capacity × 4,457) |
| Pool | K alerts shared by the team's ten experts; no limit per expert |
| Team B's equivalence (section 2, item 3) | 0.8 c + 0.2 e_i > c exactly when e_i > c, and 0.8 c + 0.2 e_i keeps the order of the e_i. Here e_i is expert i's own score and c the classifier's confidence |
| Team C's test (section 2.1) | Applicant aged 50 or over and h ≥ 0.5 |
| "Equal" in P3-G (b) | \|x − y\| ≤ 1e-5 × max(1, \|y\|); for values between 0 and 1 this is an absolute difference of at most 1e-5. y is the recomputed confidence or the fresh prediction. P3-G (f) compares exactly, with no tolerance |
| Ranking quality | Area under the receiver operating characteristic curve of the expert's own score against c, where c = 1 if the expert's decision on the alert equals the fraud label and 0 otherwise, with each alert weighted by its **fraud label**, not by c: 0.057 if legitimate, 1 if fraud, computed exactly (case weights), not by resampling; a tied pair counts one half. Both values of c therefore hold alerts of both weights. These are the router's training weights and the weights of policy 3's expected loss at 0.057 |
| Two routes (P3-G (c) and section 6) | Route 1: a standard library computation of the weighted area under the ROC curve, with case weights. Route 2: a weighted rank sum over groups of equal scores, written independently of route 1. They share only the inputs (scores, c, weights). Pass rule: \|route 1 − route 2\| ≤ 1e-9 for every model; otherwise the check fails. Values lie between 0 and 1, so this is the same as 1e-9 × max(1, \|y\|) |
| Eligible alert (section 2.2) | max over i of e_i > c, and, for team C, not (applicant aged 50 or over and h ≥ 0.5) |
| Team C test alert | Applicant aged 50 or over and h ≥ 0.5; routed to the classifier before any score comparison; counted apart from equal-score ties |
| Team B, from the rules (section 2.2 and P3-X) | With d = 1 where B defers and 0 where it keeps the expert's decision, per reviewed alert: B − policy 1 = (1 − d) × (A − policy 1), and B − A = −d × (A − policy 1) |
| Interval level | 1 − 0.05/66; ends at the percentiles 2.5/66 % and 100 − 2.5/66 % |
| Bias × capacity (section 9) | I = [m(C, 0.75) − m(A, 0.75)] − [m(C, 1) − m(A, 1)], for m in {signed age gap; count of wrongly rejected legitimate applications aged 50 or over; expected loss at 0.057}, as policy 2 section 9 |
| Equal scores (section 2, item 4) | Exact equality of the float64 values, stored values cast to float64 first. The order of the tie steps is the trees' (section 2.1) |
| Lower slot (tie step in the trees) | Policy 2's slot numbering: slot j is the team member with the j-th smallest twin number i, sorted as numbers (policy 2 section 2, item 5) |
| Split against policy 2, by seed (section 6) | Per alert and seed s: policy 3 in seed s minus policy 2 in seed s (the same review order), assigned to the classifier part or the reviewed part by where policy 3 sent the alert in seed s; then averaged over the seeds per alert, before resampling |
| Access to a reviewer by age group (section 6) | Groups: age group × policy 1's decision, from policy 1's per-alert export, joined by case. Sent to a reviewer, policy 3: the routing export's decision-maker is not the classifier. Sent to a reviewer, policy 2: the alert's position in the review order is below K, per team instance and seed. Export: both policies, one row per policy, team, version, seed, capacity and group, about 6,600 rows per policy |
| Team C's 0, exactly (section 6) | Team C's test uses the classifier score h from which policy 1's decision is taken (h ≥ 0.5), so a team C test alert and an alert of an applicant aged 50 or over that policy 1 rejects are the same alerts; check P3-C1 T7 confirms that policy 1 rejects exactly when h ≥ 0.5 |

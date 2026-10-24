# Section 5.1: who is on each team version (reviewer numbers only, entry 12), and the test-month table on team B's
# agreement with the classifier and on the decisions team C's rule changes; both formed by the summaries step. The table
# "which members two versions share" is not shown (empty by design with disjoint teams); the per-version and per-reviewer
# target and regenerated figures go to the two table files the text names (entry 13).
tv = L.csv("s_members", dtype=str)
L.save(tv, "P2-T1a_members_slot_order.csv")
num = tv.copy()
for c in [c for c in num.columns if c.startswith("slot ")]:
    num[c] = num[c].map(lambda s: s.split("#")[1])
# [analyst-23]: the tables are no longer shown; their files stay (the graph below replaces them).
L.save(L.csv("s_version_rates"), "P2-T1c_team_version_rates.csv")
L.save(L.csv("s_twins"), "P2-T1d_twins.csv")
m7 = L.csv("s_month7_items", dtype={"version": str, "capacity": str})
L.save(m7, "P2-T1e_month7_items.csv")
ITEM_NAMES = {
    "rule_c_changes_fraud": "team C: decisions on frauds changed by team C's rule",
    "rule_c_changes_legitimate": "team C: decisions on legitimate applicants changed by team C's rule",
    "team_b_measured_agreement_with_classifier": "team B: measured agreement with the classifier (share of reviewed alerts where team B's decision equals the classifier's; 1 − the override rate against the classifier)",
    "team_b_share_reviewed_twin_differs_from_classifier": "team B: share of reviewed alerts where the reviewer's own decision differs from the classifier's (supporting figure: the base of the share of disagreements where team B takes the classifier's decision; not the measured agreement)",
    "team_b_share_disagreements_deferred": "team B: share of disagreements where team B takes the classifier's decision",
}
v = m7[["team", "item", "capacity", "version", "mean over 5 seeds", "lowest seed", "highest seed"]].copy()
for c in ("mean over 5 seeds", "lowest seed", "highest seed"):
    v[c] = v[c].astype(float).round(4)
# [analyst-23], [analyst-44]: the 50 reviewers against Classifier h on the test month, in ROC space (among the alerts).
rv = L.csv("d_reviewers", dtype={"version": str}); roc = L.csv("d_roc"); pt = L.csv("d_point").iloc[0]
slope = pt["lambda"] * pt["n_legitimate"] / pt["n_frauds"]          # computed, not typed: the line of equal misclassification cost
fig, ax = plt.subplots(figsize=(7.6, 7))
ax.plot([0, 1], [0, 1], color="0.7", lw=1, ls=":")
ax.plot(roc["fpr"], roc["tpr"], color="k", lw=1.5, label="Classifier h: ROC curve")
xs = np.array([0.0, 1.0])
ax.plot(xs, pt["tpr"] + slope * (xs - pt["fpr"]), "k--", lw=1, label=f"equal misclassification cost at cost ratio {pt['lambda']:g} (slope {slope:.2f})")
cmap = plt.get_cmap("tab10")
for k, ver in enumerate(L.VERSIONS):
    d = rv[rv["version"] == ver]
    ax.plot(d["fpr"], d["tpr"], "o", ms=6, color=cmap(k), alpha=0.85, label=f"reviewers, version {ver}")
ax.plot([pt["fpr"]], [pt["tpr"]], "D", ms=10, color="k", label="Classifier h at its built-in cut-off")
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
ax.set_xlabel("FPR among the alerts (legitimate confirmed ÷ legitimate)"); ax.set_ylabel("TPR among the alerts (frauds confirmed ÷ frauds) = 1 − FNR")
ax.legend(fontsize=8, loc="lower right")
ax.set_title("The 50 reviewers against Classifier h on the test month, in ROC space (among the alerts)", fontsize=10)
fig.text(0.5, 0.0, "The curve shows Classifier h at every cut-off; the study uses only its built-in one, the diamond.", ha="center", fontsize=9)
L.savefig(fig, "P2-T1_reviewers_roc.png"); plt.show()

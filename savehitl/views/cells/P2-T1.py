# Section 5.1: who is on each team version (reviewer numbers only, entry 12), and the test-month table on team B's
# agreement with the classifier and on the decisions team C's rule changes; both formed by the summaries step. The table
# "which members two versions share" is not shown (empty by design with disjoint teams); the per-version and per-reviewer
# target and regenerated figures go to the two table files the text names (entry 13).
tv = L.csv("s_members", dtype=str)
L.save(tv, "P2-T1a_members_slot_order.csv")
num = tv.copy()
for c in [c for c in num.columns if c.startswith("slot ")]:
    num[c] = num[c].map(lambda s: s.split("#")[1])
V.show(num, 'P2-T1.df1', hide=[], rename={f'slot {i}': f'member {i + 1}' for i in range(10)}, index_names={}, column_names={}, values={}, index={}, cells=[], empty_cells=True)
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
V.show(v, 'P2-T1.df5', hide=[], rename={'mean over 5 seeds': 'average over the five random orders', 'lowest seed': 'lowest of the five random orders', 'highest seed': 'highest of the five random orders'}, index_names={}, column_names={}, values={'item': ITEM_NAMES}, index={}, cells=[], empty_cells=True)

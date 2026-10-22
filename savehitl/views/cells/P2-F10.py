# Section 3.1: graph P2-F10, naive review's deciding results in one 3 × 3 grid (entry 6), and the three table files the
# text points to (entry 7): every deciding result, the verdicts at each realistic capacity, the rule outcomes. The files
# keep the verdict texts; nothing here is shown as a table.
deciding_grid(DEC2, 2, "Naive review: the results that decide, at cost ratio 0.057 (difference from full automation, or team B or C "
              "minus team A, with its widened range)", "P2-F10_deciding_results.png")
L.save(T3, "P2-T3_deciding_results.csv")
rows = []
for comp, team in ((2, "B"), (3, "C")):
    for m, g in T3[(T3["comparison"] == comp)].groupby("measure"):
        g = g.set_index("capacity_label").reindex(L.REALISTIC)
        rows.append({"comparison": comp, "team": team, "measure": m, **{c: g.at[c, "verdict"] for c in L.REALISTIC}})
L.save(pd.DataFrame(rows), "P2-T3b_realistic_range_verdicts.csv")
r = RUL2.copy(); r["label"] = L.L_RULE
L.save(r, "P2-T3c_rule_outcomes.csv")

# Section 3.2: graph P3-F10, analyst-aware deferral's deciding results in one 3 × 3 grid with the three comparisons against
# naive review (entry 6); the table files of P3-T3.df1, df3 and df4 written, not shown (entry 7). The table of both
# policies' overall FPRs at 0.75 is no longer shown; the graph P3-F11 replaces it.
deciding_grid(DEC3, 3, "Analyst-aware deferral: the results that decide (difference from full automation, or from "
              "naive review, with its widened range)", "P3-F10_deciding_results.png")
L.save(T33, "P3-T3_deciding_results.csv")
r3 = RUL3.copy(); r3["label"] = L.L_RULE
L.save(r3, "P3-T3c_rule_outcomes.csv")
rows = []
for comp, team in ((2, "B"), (3, "C")):
    for m, g in T33[T33["comparison"] == comp].groupby("measure"):
        g = g.set_index("capacity_label").reindex(L.REALISTIC)
        rows.append({"comparison": comp, "team": team, "measure": m, **{c: g.at[c, "verdict"] for c in L.REALISTIC}})
L.save(pd.DataFrame(rows), "P3-T3b_realistic_range_verdicts.csv")

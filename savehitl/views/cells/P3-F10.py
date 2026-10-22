# Section 3.2: graph P3-F10, analyst-aware deferral's deciding results in one 3 × 3 grid with the three comparisons against
# naive review (entry 6); table P3-T3.df2 kept in the body (both policies' overall false rejection rates beside the age-gap
# result at 0.75; verdict as a symbol); the table files of P3-T3.df1, df3 and df4 written, not shown (entry 7).
deciding_grid(DEC3, 3, "Analyst-aware deferral: the results that decide, at cost ratio 0.057 (difference from full automation, or from "
              "naive review, with its widened range)", "P3-F10_deciding_results.png")
fr = [c for c in T33.columns if "overall_false_rejection_rate" in c]
g56 = T33[T33["comparison"].isin([5, 6]) & (T33["measure"] == L.mname("difference_age_gap_abs"))]
V.md('P3-T3.caption-56', "**Teams B and C at capacity 0.75 against naive review, age gap: both policies' overall false rejection rates, for each version and their average**", {})
g56 = g56.assign(verdict=L.symbols(g56["verdict"], deciding=True))
V.show(g56[["result_id", "team", "capacity_label", "estimate (mean of 5)", "verdict", "labels"] + fr].T, 'P3-T3.df2', hide=[], rename={'62': 'team B at capacity 0.75 against naive review', '65': 'team C at capacity 0.75 against naive review'}, index_names={}, column_names={}, values={}, index={'result_id': 'result', 'capacity_label': 'capacity', 'estimate (mean of 5)': 'difference (average of the five versions)', 'labels': 'note', 'overall_false_rejection_rate_team': 'overall false rejection rate, team', 'overall_false_rejection_rate_policy_1': 'overall false rejection rate, full automation', 'overall_false_rejection_rate_policy_3': 'overall false rejection rate, analyst-aware deferral (average of the five versions)', 'overall_false_rejection_rate_policy_2': 'overall false rejection rate, naive review (average of the five versions)', 'v1_overall_false_rejection_rate_policy_3': 'version 1: overall false rejection rate, analyst-aware deferral', 'v1_overall_false_rejection_rate_policy_2': 'version 1: overall false rejection rate, naive review', 'v2_overall_false_rejection_rate_policy_3': 'version 2: overall false rejection rate, analyst-aware deferral', 'v2_overall_false_rejection_rate_policy_2': 'version 2: overall false rejection rate, naive review', 'v3_overall_false_rejection_rate_policy_3': 'version 3: overall false rejection rate, analyst-aware deferral', 'v3_overall_false_rejection_rate_policy_2': 'version 3: overall false rejection rate, naive review', 'v4_overall_false_rejection_rate_policy_3': 'version 4: overall false rejection rate, analyst-aware deferral', 'v4_overall_false_rejection_rate_policy_2': 'version 4: overall false rejection rate, naive review', 'v5_overall_false_rejection_rate_policy_3': 'version 5: overall false rejection rate, analyst-aware deferral', 'v5_overall_false_rejection_rate_policy_2': 'version 5: overall false rejection rate, naive review'}, cells=[['result_id', '62', 'policy 3, comparison 5, absolute age gap', 'size of the age gap'], ['result_id', '65', 'policy 3, comparison 6, absolute age gap', 'size of the age gap']], empty_cells=True)
L.save(T33, "P3-T3_deciding_results.csv")
r3 = RUL3.copy(); r3["label"] = L.L_RULE
L.save(r3, "P3-T3c_rule_outcomes.csv")
rows = []
for comp, team in ((2, "B"), (3, "C")):
    for m, g in T33[T33["comparison"] == comp].groupby("measure"):
        g = g.set_index("capacity_label").reindex(L.REALISTIC)
        rows.append({"comparison": comp, "team": team, "measure": m, **{c: g.at[c, "verdict"] for c in L.REALISTIC}})
L.save(pd.DataFrame(rows), "P3-T3b_realistic_range_verdicts.csv")

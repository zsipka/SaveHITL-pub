# Section 6.8: table rows-0035, expected loss against "confirm every alert" at cost ratio 0.035, read from the run's own
# descriptive exports by their key columns (not by line number); verdict as a symbol. The keys are the study's
# rows; the analyst confirms them from the advance execution.
R2 = keyed_rows("p2_desc", [("vs_confirm_every_alert", L.MEAN5, "C", "0.15", "0.035", "difference_expected_loss")])
R2["verdict"] = L.symbols(R2["verdict"])
V.show(R2, 'rows-0035.df1', hide=[], rename={'comparison name': 'comparison', 'capacity_label': 'capacity', 'lambda': 'cost ratio', 'measure name': 'measure', 'point_estimate': 'difference (average of the five versions)', 'ci_low': '95% range, low', 'ci_high': '95% range, high', 'verdict': 'verdict (descriptive)'}, index_names={}, column_names={}, values={'comparison name': {'against confirming every alert': 'against "confirm every alert"'}, 'measure name': {'expected loss, difference': 'expected loss'}}, index={}, cells=[], empty_cells=True)
R3 = keyed_rows("p3_desc", [("vs_confirm_every_alert", L.MEAN5, t, c, "0.035", "difference_expected_loss") for c in ("0.75", "1.00") for t in L.TEAMS])
R3["verdict"] = L.symbols(R3["verdict"])
V.show(R3, 'rows-0035.df2', hide=[], rename={'comparison name': 'comparison', 'capacity_label': 'capacity', 'lambda': 'cost ratio', 'measure name': 'measure', 'point_estimate': 'difference (average of the five versions)', 'ci_low': '95% range, low', 'ci_high': '95% range, high', 'verdict': 'verdict (descriptive)'}, index_names={}, column_names={}, values={'comparison name': {'against confirming every alert': 'against "confirm every alert"'}, 'measure name': {'expected loss, difference': 'expected loss'}}, index={}, cells=[], empty_cells=True)
L.save(pd.concat([R2, R3], ignore_index=True), "rows-0035.csv")

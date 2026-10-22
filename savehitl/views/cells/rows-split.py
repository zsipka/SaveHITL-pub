# Section 3.3: table rows-split, the two parts of analyst-aware deferral minus naive review, on both measures, read from
# the run's own descriptive export by their key columns (not by line number); verdict as a symbol.
SPLIT_KEYS = [("vs_policy_2", L.MEAN5, t, c, lam, m) for t, c in (("A", "1.00"), ("B", "0.75"), ("C", "0.75"))
              for lam, m in (("0.057", "classifier_part_expected_loss"), ("0.057", "reviewed_part_expected_loss"),
                             ("", "classifier_part_accepted_frauds"), ("", "reviewed_part_accepted_frauds"))]
RS = keyed_rows("p3_desc", SPLIT_KEYS)
RS["verdict"] = L.symbols(RS["verdict"])
V.show(RS, 'rows-split.df1', hide=[], rename={'comparison name': 'comparison', 'capacity_label': 'capacity', 'lambda': 'cost ratio', 'measure name': 'measure', 'point_estimate': 'difference (average of the five versions)', 'ci_low': '95% range, low', 'ci_high': '95% range, high', 'verdict': 'verdict (descriptive)'}, index_names={}, column_names={}, values={'comparison name': {'against policy 2': 'against naive review'}, 'measure name': {'expected loss, classifier part': 'expected loss: alerts left to the classifier', 'expected loss, reviewed-cases part': 'expected loss: alerts reviewed', 'regulatory exposure (accepted frauds), classifier part': 'frauds accepted: alerts left to the classifier', 'regulatory exposure (accepted frauds), reviewed-cases part': 'frauds accepted: alerts reviewed'}}, index={}, cells=[], empty_cells=True)
L.save(RS, "rows-split.csv")

# Section 6.6: table P3-T7 (verdict as a symbol).
t = BX3[["team", "version", "capacity_label", "measure", "point_estimate", "ci_low", "ci_high", "verdict", "reading", "kind"]].copy()
t["measure"] = t["measure"].map(L.mname); t["label"] = L.L_DESC
V.show(t.assign(verdict=L.symbols(t["verdict"])), 'P3-T7.df1', hide=['label'], rename={'capacity_label': 'capacities compared', 'point_estimate': 'change (point figure)', 'ci_low': '95% range, low', 'ci_high': '95% range, high'}, index_names={}, column_names={}, values={}, index={}, cells=[], empty_cells=True); L.save(t, "P3-T7_bias_x_capacity.csv")
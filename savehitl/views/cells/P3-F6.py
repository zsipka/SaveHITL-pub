# Section 6.8: graph P3-F6 and its label grid.
verdict_grid(CL3, 'Analyst-aware deferral: expected-loss verdict against full automation at each cost ratio and capacity', "P3-F6_cost_ratio_grid.png")
t = CL3[CL3["version"].astype(str) == L.MEAN5].copy(); t["label"] = L.L_DESC
add_u_label(t, CL3, "P3-U label")
L.save(t, "P3-F6_cost_ratio_labels.csv")
show_u_label(t, "P3-U label", "p3_costlab", dict(key='P3-F6.df1', hide=[], rename={}, index_names={}, column_names={'capacity_label': 'capacity'}, values={}, index={}, cells=[], empty_cells=True))
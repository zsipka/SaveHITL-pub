# Section 4.8 (round 2): graph P3-F6 (item "P3-F6", both notebooks); its label grid is shown by the item "P3-F6-tables"
# (long notebook, appendix A.8). Both parts write the same table file.
t = CL3[CL3["version"].astype(str) == L.MEAN5].copy(); t["label"] = L.L_DESC
add_u_label(t, CL3, "P3-U label")
L.save(t, "P3-F6_cost_ratio_labels.csv")
if PART != "tables":
    verdict_grid(CL3, 'Analyst-aware deferral: expected-loss verdict against full automation at each cost ratio and capacity', "P3-F6_cost_ratio_grid.png")
if PART != "graph":
    show_u_label(t, "P3-U label", "p3_costlab", dict(key='P3-F6.df1', hide=[], rename={}, index_names={}, column_names={'capacity_label': 'capacity'}, values={}, index={}, cells=[], empty_cells=True))

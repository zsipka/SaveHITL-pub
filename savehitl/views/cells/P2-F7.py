# Section 4.8 (round 2): graph P2-F7 (item "P2-F7", both notebooks); its label table (verdicts as symbols) and the label
# grid are shown by the item "P2-F7-tables" (long notebook, appendix A.8). Both parts write the same table file.
t = CL2[CL2["version"].astype(str) == L.MEAN5].copy(); t["label"] = L.L_DESC
add_u_label(t, CL2, "P2-U label")
L.save(t, "P2-F7_cost_ratio_labels.csv")
if PART != "tables":
    verdict_grid(CL2, 'Naive review: expected-loss verdict against full automation at each cost ratio and capacity', "P2-F7_cost_ratio_grid.png")
if PART != "graph":
    tv = t[t["label"].notna() & t["qualifier"].notna()].copy()
    for c in [c for c in tv.columns if c.startswith("verdict_")]:
        tv[c] = L.symbols(tv[c])
    V.show(tv, 'P2-F7.df1', hide=['label'], rename={'capacity_label': 'capacity', 'beats_at': 'beats full automation at cost ratios', 'does_worse_at': 'does worse at cost ratios', 'verdict_0.035': 'verdict at 0.035', 'verdict_0.0537': 'verdict at 0.0537', 'verdict_0.057': 'verdict at 0.057', 'verdict_0.171': 'verdict at 0.171', 'break_even_notes': 'where the break-even lies', 'P2-U label': 'across cost ratios'}, index_names={}, column_names={}, values={}, index={}, cells=[], empty_cells=True)
    show_u_label(t, "P2-U label", "p2_costlab", dict(key='P2-F7.df2', hide=[], rename={}, index_names={}, column_names={'capacity_label': 'capacity'}, values={}, index={}, cells=[], empty_cells=True))

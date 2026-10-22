# Policy 3 outputs used by the views (verdict tables of step verdicts3; routing and cell measures of step policy3).
D3 = L.desc_load("p3_desc"); DEC3 = L.csv("p3_dec", dtype={"capacity_label": str}); RUL3 = L.csv("p3_rules")
BND3 = L.csv("p3_bound", dtype={"version": str}); CH3 = L.csv("p3_chance"); CL3 = L.csv("p3_costlab", dtype={"version": str, "capacity_label": str})
BX3 = L.desc_load("p3_bxc"); CELLS3 = L.csv("p3_cells", dtype={"version": str, "capacity_label": str})
for df in (CELLS3, DEC3, CL3):
    df["capacity_label"] = df["capacity_label"].map(L.cap_label)
ROUT = L.csv("p3_routing", dtype={"version": str, "capacity_label": str}); ROUT["capacity_label"] = ROUT["capacity_label"].map(L.cap_label)
T33 = dec_table(DEC3, L.L_P3_DEC)

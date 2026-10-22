# Policy 2 outputs used by the views (verdict tables of step verdicts2, cell measures of step policy2).
D2 = L.desc_load("p2_desc"); DEC2 = L.csv("p2_dec", dtype={"capacity_label": str}); RUL2 = L.csv("p2_rules")
BND2 = L.csv("p2_bound", dtype={"version": str}); CH2 = L.csv("p2_chance"); CL2 = L.csv("p2_costlab", dtype={"version": str, "capacity_label": str})
BX2 = L.desc_load("p2_bxc"); CELLS2 = L.csv("p2_cells", dtype={"version": str, "capacity_label": str})
CELLS2["capacity_label"] = CELLS2["capacity_label"].map(L.cap_label)
DEC2["capacity_label"] = DEC2["capacity_label"].map(L.cap_label)
CL2["capacity_label"] = CL2["capacity_label"].map(L.cap_label)
RM2 = L.record("policy2")
T3 = dec_table(DEC2, L.L_P2_DEC, L.L_P2K)

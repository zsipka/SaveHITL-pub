# Section 6.4: FPRs over every application of the test month, descriptive ([analyst-20], [analyst-40]). FP per age group
# as the deciding measures count it (cell measures of steps policy2 and policy3; mean over the five random orders and the
# five versions), divided by the legitimate applications of month 7 in that group (step applications). Applications the
# Alert Model did not flag count as accepted (FP = 0 outside the alerts). Full automation from step descriptive.
tm = L.csv("a_test_month").set_index("age_group")
fpfn = L.csv("d_fpfn", dtype={"version": str, "team": str, "capacity": str}, keep_default_na=False)
L._ASSERT.check(bool((tm["n_legitimate"] >= L.MIN_GROUP).all()), "every displayed figure over at least 10 applications", panel="P3-T10")
GROUPS = [("50 or over", "false_rejections_50_plus", "FPR₅₀₊"), ("under 50", "false_rejections_under_50", "FPR<₅₀"), ("all ages", "false_rejections_count", "overall FPR")]
rows = []
r = {"policy": "full automation", "team": "—", "capacity": "—"}
for grp, _, name in GROUPS:
    f = fpfn[(fpfn["policy"] == "full automation") & (fpfn["age_group"] == grp)]
    r[name] = round(float(f["fp"].iloc[0]) / tm.at[grp, "n_legitimate"], 4)
rows.append(r)
for pol, cells in (("naive review", CELLS2), ("analyst-aware deferral", CELLS3)):
    c = cells[L.lam_eq(cells["lambda"], 0.057)]
    for team, cap in (("A", "1.00"), ("B", "0.75"), ("C", "0.75")):
        d = c[(c["team"] == team) & (c["capacity_label"] == cap)]
        assert len(d) == 25, (pol, team, cap, len(d))
        r = {"policy": pol, "team": team, "capacity": cap.replace("1.00", "1")}
        for grp, col, name in GROUPS:
            r[name] = round(float(d[col].mean()) / tm.at[grp, "n_legitimate"], 4)
        rows.append(r)
V.md("P3-T10.caption", "**FPRs on every application of the test month, descriptive; applications the Alert Model did not flag count as accepted "
     "(at the deciding comparisons; average of the five versions and five random orders)**", {})
V.show(pd.DataFrame(rows).set_index(["policy", "team", "capacity"]), "P3-T10.df1", empty_cells=True)

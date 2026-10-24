# Section 4.7 (round 2): graph P2-F5 (item "P2-F5", both notebooks); its table, verdict as a symbol, with the caption
# line "FPR among the alerts" (C14), is shown by the item "P2-F5-table" (long notebook, appendix A.6). Both parts write
# the same table file.
bt = BX2[["team", "version", "capacity_label", "measure", "point_estimate", "ci_low", "ci_high", "verdict", "reading", "kind"]].copy(); bt["measure"] = bt["measure"].map(L.mname); bt["label"] = L.L_DESC
if PART != "tables":
    fig, axs = plt.subplots(1, 5, figsize=(24, 6.2), gridspec_kw={"width_ratios": [3, 3, 1, 1, 1]})
    for team, ls in (("A", "-"), ("C", "--")):
        for m, col in (("false_positive_rate_50_plus", "tab:red"), ("false_positive_rate_under_50", "tab:blue")):
            d = D2[(D2["comparison"] == "level") & (D2["team"] == team) & (D2["version"] == L.MEAN5) & (D2["measure"] == m)].sort_values("cap")
            axs[0].plot(d["cap"], d["point_estimate"], ls=ls, color=col, label=V.txt('P2-F5.legend-rate', 'team {team}, {measure}', {}, team=team, measure=L.mname(m)))
            axs[0].fill_between(d["cap"], d["ci_low"], d["ci_high"], color=col, alpha=0.1)
    axs[0].set_xlabel('capacity'); axs[0].set_ylabel('FPR among the alerts'); axs[0].legend(fontsize=9); axs[0].set_title('false rejection rates by age group\n(average of the five versions, 95% band)')
    g = D2[(D2["comparison"] == "C_minus_A") & (D2["version"] == L.MEAN5) & (D2["measure"] == "difference_age_gap_signed")].sort_values("cap")
    g1 = g[g["capacity_label"] == "1.00"]["point_estimate"].iloc[0]
    axs[1].plot(g["cap"], g["point_estimate"], "o-", ms=3, label='observed team C minus team A signed age gap (average of the five versions)')
    axs[1].fill_between(g["cap"], g["seed_min"], g["seed_max"], alpha=0.2, label='range over the five random orders')
    axs[1].plot(g["cap"], g["cap"] * g1, "k:", label='line expected if the bias scaled with capacity: capacity × gap at full capacity')
    axs[1].set_xlabel('capacity'); axs[1].legend(fontsize=9); axs[1].set_title('team C minus team A gap against the line\nexpected if the bias scaled with capacity')
    b = BX2[BX2["version"] == L.MEAN5].copy(); b["metric"] = b["measure"].map(L.mname)
    for ax, (_, rr) in zip(axs[2:], b.iterrows()):
        ax.errorbar([0], [rr["point_estimate"]], yerr=[[rr["point_estimate"] - rr["ci_low"]], [rr["ci_high"] - rr["point_estimate"]]], fmt="o", capsize=4)
        ax.axhline(0, color="k", lw=0.8); ax.set_xticks([]); ax.set_title(V.txt('P2-F5.panel-i', 'change between capacity 0.75\nand full capacity:\n{metric}\n{reading};\n{kind}', {}, metric=rr['metric'], reading=rr['reading'], kind=rr['kind']), fontsize=9)
    fig.suptitle("Naive review: false rejection rates by age group for teams C and A against capacity, and how team C's bias changes between capacity 0.75 and full capacity", y=1.0); fig.tight_layout(rect=(0, 0, 1, 0.94)); L.savefig(fig, "P2-F5_bias_x_capacity.png"); plt.show()
if PART != "graph":
    V.show(bt.assign(verdict=L.symbols(bt["verdict"])), 'P2-F5.df1', hide=['label'], rename={'capacity_label': 'capacities compared', 'point_estimate': 'change (point figure)', 'ci_low': '95% range, low', 'ci_high': '95% range, high'}, index_names={}, column_names={}, values={}, index={}, cells=[], empty_cells=True)
    V.md("fpr.reminder", "*" + L.FPR_REMINDER + "*", {})
L.save(bt, "P2-F5_bias_x_capacity_I.csv")

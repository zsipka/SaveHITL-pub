# Section 4.6 (round 5; 4.7 in round 2): graph P2-F5 (item "P2-F5", both notebooks); its table, verdict as a symbol, with the caption
# line "FPR among the alerts" (C14), is shown by the item "P2-F5-table" (long notebook, appendix A.6). Both parts write
# the same table file.
bt = BX2[["team", "version", "capacity_label", "measure", "point_estimate", "ci_low", "ci_high", "verdict", "reading", "kind"]].copy(); bt["measure"] = bt["measure"].map(L.mname); bt["label"] = L.L_DESC
if PART != "tables":
    # Round 5 ([analyst-48]): two rows. Row 1: FPRs by age group, misclassification cost, empty. Row 2: the gap against
    # capacity, signed age gap, count aged 50 or over. Wide graphs in the first column, small panels as before; no shared y.
    fig = plt.figure(figsize=(23, 14))
    gs = fig.add_gridspec(2, 3, width_ratios=[3, 1, 1], wspace=0.8, hspace=0.42)
    ax_fpr, ax_gap = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0])
    small = {"expected_loss": fig.add_subplot(gs[0, 1]), "age_gap_signed": fig.add_subplot(gs[1, 1]),
             "50_plus_count": fig.add_subplot(gs[1, 2])}     # position 1.3 (gs[0, 2]) stays empty, with no axes
    for team, ls in (("A", "-"), ("C", "--")):
        for m, col in (("false_positive_rate_50_plus", "tab:red"), ("false_positive_rate_under_50", "tab:blue")):
            d = D2[(D2["comparison"] == "level") & (D2["team"] == team) & (D2["version"] == L.MEAN5) & (D2["measure"] == m)].sort_values("cap")
            ax_fpr.plot(d["cap"], d["point_estimate"], ls=ls, color=col, label=V.txt('P2-F5.legend-rate', 'team {team}, {measure}', {}, team=team, measure=L.mname(m)))
            ax_fpr.fill_between(d["cap"], d["ci_low"], d["ci_high"], color=col, alpha=0.1)
    import matplotlib.patches as mpatches
    h_, l_ = ax_fpr.get_legend_handles_labels()       # [analyst-47]: one entry for the four shaded bands
    h_.append(mpatches.Patch(facecolor="0.5", alpha=0.3, label="shaded: 95% range over the re-drawn cases"))
    ax_fpr.set_xlabel('capacity'); ax_fpr.set_ylabel('FPR among the alerts'); ax_fpr.legend(handles=h_, fontsize=9, loc="lower left")
    ax_fpr.set_title('false rejection rates by age group\n(average of the five versions, 95% range over the re-drawn cases)')
    g = D2[(D2["comparison"] == "C_minus_A") & (D2["version"] == L.MEAN5) & (D2["measure"] == "difference_age_gap_signed")].sort_values("cap")
    g1 = g[g["capacity_label"] == "1.00"]["point_estimate"].iloc[0]
    ax_gap.plot(g["cap"], g["point_estimate"], "o-", ms=3, label='observed team C minus team A signed age gap (average of the five versions)')
    ax_gap.fill_between(g["cap"], g["seed_min"], g["seed_max"], alpha=0.2, label='range over the five random orders')
    ax_gap.plot(g["cap"], g["cap"] * g1, "k:", label='line expected if the bias scaled with capacity: capacity × gap at full capacity')
    ax_gap.set_xlabel('capacity'); ax_gap.legend(fontsize=9); ax_gap.set_title('team C minus team A gap against the line\nexpected if the bias scaled with capacity')
    b = BX2[BX2["version"] == L.MEAN5].copy(); b["metric"] = b["measure"].map(L.mname)
    placed = []
    for _, rr in b.iterrows():
        key = [k for k in small if k in rr["measure"]]
        assert len(key) == 1, rr["measure"]
        ax = small[key[0]]; placed.append(key[0])
        ax.errorbar([0], [rr["point_estimate"]], yerr=[[rr["point_estimate"] - rr["ci_low"]], [rr["ci_high"] - rr["point_estimate"]]], fmt="o", capsize=4)
        ax.axhline(0, color="k", lw=0.8); ax.set_xticks([])
        ax.set_title(V.txt('P2-F5.panel-i', "{metric}: team C's excess over team A\nat capacity 0.75 minus at full capacity\n{reading}; {kind}", {}, metric=rr['metric'], reading=rr['reading'], kind=rr['kind']), fontsize=9)
        ax.set_ylabel("change in team C's excess (below zero: smaller at 0.75)", fontsize=9)
    assert sorted(placed) == sorted(small), placed
    fig.suptitle("Naive review: false rejection rates by age group for teams C and A against capacity, and how team C's bias changes between capacity 0.75 and full capacity", y=0.995)
    L.savefig(fig, "P2-F5_bias_x_capacity.png"); plt.show()
if PART != "graph":
    V.show(bt.assign(verdict=L.symbols(bt["verdict"])), 'P2-F5.df1', hide=['label'], rename={'capacity_label': 'capacities compared', 'point_estimate': 'change (point figure)', 'ci_low': '95% range, low', 'ci_high': '95% range, high'}, index_names={}, column_names={}, values={}, index={}, cells=[], empty_cells=True)
    V.md("fpr.reminder", "*" + L.FPR_REMINDER + "*", {})
L.save(bt, "P2-F5_bias_x_capacity_I.csv")

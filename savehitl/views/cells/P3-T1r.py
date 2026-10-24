# Section 4.1: the router's ranking quality per team version, test month beside the previous month, as formed by the
# summaries step from the ranking step's per-model figures (no third row). The per-model figures are
# written to the table files.
rk7 = L.csv("p3_rank_model"); rk6 = L.csv("p3_rank_month6_model")
L.save(rk7, "P3-T1b_ranking_quality_per_model_month7.csv"); L.save(rk6, "P3-T1b_ranking_quality_per_model_month6.csv")
byv = L.csv("s_ranking", dtype={"team_version": str}).set_index("team_version")
L.save(byv.reset_index(), "P3-T1c_ranking_quality_by_version.csv")
# [analyst-06]: the table is replaced by a dot-and-range graph (average of the version's 50 models; lowest to highest).
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(len(byv))
for k, (mon, name, dx, filled) in enumerate(((7, "test month", -0.12, True), (6, "previous month", 0.12, False))):
    av = byv[f"month {mon} average of 50 models"].astype(float).values
    lo = byv[f"month {mon} lowest model"].astype(float).values; hi = byv[f"month {mon} highest model"].astype(float).values
    ax.vlines(x + dx, lo, hi, color="tab:blue", lw=1.6)
    ax.plot(x + dx, av, "o", ms=8, color="tab:blue", markerfacecolor="tab:blue" if filled else "white", markeredgewidth=1.6,
            label=f"{name}: average of the version's 50 models (bar: lowest to highest)")
ax.axhline(0.5, color="k", ls="--", lw=1, label="0.5: chance")
ax.set_xticks(x); ax.set_xticklabels([f"version {v}" if str(v).isdigit() else str(v) for v in byv.index])   # C18: "all 250 models"
ax.set_ylabel("ranking quality\n(weighted area under the ROC curve)")   # C18: in two lines, not clipped
ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
ax.set_title("How well the router ranks, per team version", fontsize=10)
L.savefig(fig, "P3-T1r_ranking_quality.png"); plt.show()

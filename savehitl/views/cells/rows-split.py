# Section 3.3: table rows-split, the two parts of analyst-aware deferral minus naive review, on both measures, read from
# the run's own descriptive export by their key columns (not by line number); verdict as a symbol.
SPLIT_KEYS = [("vs_policy_2", L.MEAN5, t, c, lam, m) for t, c in (("A", "1.00"), ("B", "0.75"), ("C", "0.75"))
              for lam, m in (("0.057", "classifier_part_expected_loss"), ("0.057", "reviewed_part_expected_loss"),
                             ("", "classifier_part_accepted_frauds"), ("", "reviewed_part_accepted_frauds"))]
RS = keyed_rows("p3_desc", SPLIT_KEYS)
RS["verdict"] = L.symbols(RS["verdict"])     # as before: the table file holds the symbols
# [analyst-04]: the table is replaced by a range graph.
L.save(RS, "rows-split.csv")
VC = {"beats": "tab:green", "does worse": "tab:red", "no difference shown": "goldenrod"}
PART = {"classifier": "left to the classifier", "reviewed": "reviewed"}
COMP = {("A", "1.00"): "team A at 1", ("B", "0.75"): "team B at 0.75", ("C", "0.75"): "team C at 0.75"}
raw = keyed_rows("p3_desc", SPLIT_KEYS)
raw["part"] = [PART["classifier" if "classifier part" in m else "reviewed"] for m in raw["measure name"]]
raw["panel"] = ["misclassification cost, difference (cost ratio 0.057)" if "expected loss" in m else "frauds accepted, difference" for m in raw["measure name"]]
fig, axs = plt.subplots(1, 2, figsize=(14, 4.6))
for ax, panel in zip(axs, dict.fromkeys(raw["panel"])):
    g = raw[raw["panel"] == panel].reset_index(drop=True)
    y = np.arange(len(g))[::-1]
    for yy, (_, r) in zip(y, g.iterrows()):
        c = VC.get(r["verdict"], "0.5")
        ax.errorbar([r["point_estimate"]], [yy], xerr=[[r["point_estimate"] - r["ci_low"]], [r["ci_high"] - r["point_estimate"]]], fmt="o", color=c, capsize=3, ms=7)
        ax.annotate(f"{r['point_estimate']:.1f}", (r["point_estimate"], yy), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8)
    ax.axvline(0, color="k", lw=0.9, ls="--")
    ax.set_yticks(y); ax.set_yticklabels([f"{COMP[(t, c)]}: {p}" for t, c, p in zip(g["team"], g["capacity_label"], g["part"])], fontsize=9)
    ax.set_title(panel, fontsize=10); ax.set_xlabel("analyst-aware deferral minus naive review (average of the five versions, 95% range)")
import matplotlib.lines as mlines
fig.legend(handles=[mlines.Line2D([], [], color=c, marker="o", ls="none", label=v) for v, c in VC.items()], loc="lower center", ncol=3, fontsize=9,
           frameon=False, bbox_to_anchor=(0.5, -0.08))
fig.suptitle("Analyst-aware deferral minus naive review at the three deciding comparisons, split into the alerts left to the classifier and the alerts reviewed")
fig.tight_layout(); L.savefig(fig, "rows-split_parts_range.png"); plt.show()

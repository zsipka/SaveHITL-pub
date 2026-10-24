# Section 6.8: table rows-0035, expected loss against "confirm every alert" at cost ratio 0.035, read from the run's own
# descriptive exports by their key columns (not by line number); verdict as a symbol. The keys are the study's
# rows; the analyst confirms them from the advance execution.
R2 = keyed_rows("p2_desc", [("vs_confirm_every_alert", L.MEAN5, "C", "0.15", "0.035", "difference_expected_loss")])
R2["verdict"] = L.symbols(R2["verdict"])
R3 = keyed_rows("p3_desc", [("vs_confirm_every_alert", L.MEAN5, t, c, "0.035", "difference_expected_loss") for c in ("0.75", "1.00") for t in L.TEAMS])
R3["verdict"] = L.symbols(R3["verdict"])
L.save(pd.concat([R2, R3], ignore_index=True), "rows-0035.csv")
# [analyst-08]: the two tables are replaced by one range graph; the table file keeps the texts and symbols.
VC = {"✅": "tab:green", "❌": "tab:red", "🟡": "goldenrod"}
G = pd.concat([R2.assign(pol="naive review"), R3.assign(pol="analyst-aware deferral")], ignore_index=True)
fig, ax = plt.subplots(figsize=(10, 4.4))
y = np.arange(len(G))[::-1]
for yy, (_, r) in zip(y, G.iterrows()):
    c = VC.get(str(r["verdict"]).rstrip("*"), "0.5")
    ax.errorbar([r["point_estimate"]], [yy], xerr=[[r["point_estimate"] - r["ci_low"]], [r["ci_high"] - r["point_estimate"]]], fmt="o", color=c, capsize=3, ms=7)
ax.axvline(0, color="k", lw=0.9, ls="--")
ax.set_yticks(y); ax.set_yticklabels([f"{p}, team {t} at {c.replace('1.00', '1')}" for p, t, c in zip(G["pol"], G["team"], G["capacity_label"])], fontsize=9)
ax.set_xlabel('misclassification-cost difference from "confirm every alert" at cost ratio 0.035\n(average of the five versions, 95% range; below zero: the policy costs less)')
import matplotlib.lines as mlines
ax.legend(handles=[mlines.Line2D([], [], color=c, marker="o", ls="none", label=v) for v, c in (("beats", "tab:green"), ("no difference shown", "goldenrod"), ("does worse", "tab:red"))],
          fontsize=8, loc="best")
ax.set_title('Against "confirm every alert" at cost ratio 0.035', fontsize=10)
L.savefig(fig, "rows-0035_range.png"); plt.show()

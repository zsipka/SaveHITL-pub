# The data and the set-up: what the applications show (panels D1 to D5). Aggregates only, each over at least 10
# applications (the step applications merges or drops smaller groups and stops otherwise); no point per application,
# no box plot, no histogram, and no axis taken from a column's minimum or maximum: the month axis is the fixed list 0 to 7,
# the age axis the list of stored age groups, and the value axes are fitted to the plotted aggregates.
am = L.csv("a_month"); aa = L.csv("a_age", dtype={"age_group": str}); ama = L.csv("a_month_age"); sp = L.csv("a_spearman")
ac = L.csv("a_columns"); fl = L.csv("a_flag", dtype={"age_group": str})
for name, d, n in (("D1", am, "n_applications"), ("D2", aa, "n_applications"), ("D5", fl, "n_legitimate"), ("D4", sp, "n_applications")):
    L._ASSERT.check(bool((d[n] >= L.MIN_GROUP).all()), "every displayed figure over at least 10 applications", panel=name)
L._ASSERT.check(bool((ama.loc[ama["shown"], "n_applications"] >= L.MIN_GROUP).all()), "every displayed figure over at least 10 applications", panel="D3")
overall = am["n_frauds"].sum() / am["n_applications"].sum()
fig = plt.figure(figsize=(19, 12.5))
gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.55], hspace=0.38, wspace=0.28)
# D1
ax = fig.add_subplot(gs[0, 0])
ax.bar(am["month"], am["n_applications"], color=["#c7c7c7"] * 7 + ["#8c8c8c"], edgecolor=["none"] * 7 + ["k"])
ax.set_xticks(range(8)); ax.set_xlabel("month"); ax.set_ylabel("applications (bars)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k"))
a2 = ax.twinx(); a2.plot(am["month"], 100 * am["fraud_rate"], "o-", color="tab:red"); a2.set_ylabel("share of frauds, % (line)", color="tab:red")
a2.margins(y=0.25)
ax.set_title("D1. Applications and fraud rate, per month\n(test month outlined)", fontsize=10)
# D2
ax = fig.add_subplot(gs[0, 1])
x = np.arange(len(aa))
old = aa["age_50_plus"] == 1
if old.any():
    ax.axvspan(x[old.values].min() - 0.5, x[old.values].max() + 0.5, color="0.92", zorder=0, label="aged 50 or over")
ax.fill_between(x, 100 * aa["fraud_rate_wilson_low"], 100 * aa["fraud_rate_wilson_high"], color="tab:red", alpha=0.25, label="95% range (Wilson)")
ax.plot(x, 100 * aa["fraud_rate"], "o-", color="tab:red", label="fraud rate")
ax.axhline(100 * overall, color="k", ls="--", lw=1, label="all ages")
ax.set_xticks(x); ax.set_xticklabels(aa["age_group"]); ax.set_xlabel("applicant age group (years, as stored)"); ax.set_ylabel("fraud rate, %")
ax.legend(fontsize=8, loc="upper left"); ax.set_title("D2. Fraud rate by applicant age group", fontsize=10)
# D3
ax = fig.add_subplot(gs[0, 2])
ax.axvspan(6.5, 7.5, color="#fff2cc", zorder=0)
for grp, col in (("under 50", "tab:blue"), ("50 or over", "tab:red")):
    d = ama[(ama["age_group"] == grp) & ama["shown"]].sort_values("month")
    ax.plot(d["month"], 100 * d["fraud_rate"], "o-", color=col, label=grp)
ax.set_xticks(range(8)); ax.set_xlabel("month (test month shaded)"); ax.set_ylabel("fraud rate, %"); ax.legend(fontsize=8)
ax.set_title("D3. Fraud rate under 50 and 50 or over, per month", fontsize=10)
# D4
ax = fig.add_subplot(gs[1, 0:2])
cols = list(dict.fromkeys(sp["row"]))
n = len(cols)
M = np.full((n, n), np.nan)
pos = {c: i for i, c in enumerate(cols)}
for _, r in sp.iterrows():
    M[pos[r["row"]], pos[r["column"]]] = r["spearman"]
im = ax.imshow(np.ma.masked_invalid(M), cmap="RdBu_r", vmin=-1, vmax=1)
for i in range(n):
    for j in range(i + 1):
        if not np.isnan(M[i, j]):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=5.6, color="white" if abs(M[i, j]) > 0.6 else "k")
ax.set_xticks(range(n)); ax.set_xticklabels(cols, rotation=90, fontsize=7.5); ax.set_yticks(range(n)); ax.set_yticklabels(cols, fontsize=7.5)
for t in ax.get_yticklabels()[:2] + ax.get_xticklabels()[:2]:
    t.set_fontweight("bold"); t.set_color("darkred")
for s in ax.spines.values():
    s.set_visible(False)
fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
ax.set_title("D4. Spearman correlation of the label and the numeric features (lower triangle; colour from −1 to +1)", fontsize=10)
# round-2 [analyst-36]: the note on left-out features is no longer in the figure; the notebook lists them under it.
# D5
ax = fig.add_subplot(gs[1, 2])
x = np.arange(len(fl))
old = fl["age_50_plus"] == 1
if old.any():
    ax.axvspan(x[old.values].min() - 0.5, x[old.values].max() + 0.5, color="0.92", zorder=0, label="aged 50 or over")
ax.fill_between(x, 100 * fl["share_flagged_wilson_low"], 100 * fl["share_flagged_wilson_high"], color="tab:purple", alpha=0.25, label="95% range (Wilson)")
ax.plot(x, 100 * fl["share_flagged"], "o-", color="tab:purple", label="share flagged")
ax.axhline(100 * fl["n_flagged"].sum() / fl["n_legitimate"].sum(), color="k", ls="--", lw=1, label="all ages")
ax.set_xticks(x); ax.set_xticklabels(fl["age_group"]); ax.set_xlabel("applicant age group (years, as stored)")
ax.set_ylabel("legitimate applicants flagged, %"); ax.legend(fontsize=8, loc="upper left")
ax.set_title("D5. Share of legitimate applicants the Alert Model flags,\nby age group, months 3 to 7", fontsize=10)
fig.suptitle("What the applications show: label, age and features", fontsize=13, y=0.97)
L.savefig(fig, "F-data_applications.png"); plt.show()

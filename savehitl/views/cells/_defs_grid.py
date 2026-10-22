# The 3 × 3 graph of the deciding results of one policy (notebook change log entry 6): rows the measures (the age-gap row
# is the absolute age gap), columns the teams, x the realistic capacity, y the difference with its widened (deciding)
# range, colour the verdict. Against full automation: round markers. Policy 2: teams B and C against team A at 0.75 as
# diamonds; the two results fixed by construction (route P2-K) hollow, the signed age gap labelled "signed". Policy 3:
# the three comparisons against naive review as squares with a dark blue edge and range. Drawn from the deciding table
# as the verdict step wrote it; nothing is computed.
GRID_ROWS = [("difference_expected_loss", "expected loss, difference"), ("difference_accepted_frauds", "frauds accepted, difference"),
             ("difference_age_gap_abs", "size of the age gap, difference")]
VERDICT_COLOUR = {"beats": "tab:green", "does worse": "tab:red", "no difference shown": "goldenrod"}


def deciding_grid(DEC, policy, title, fname):
    import matplotlib.lines as mlines
    d = DEC.copy()
    d["cap"] = d["capacity_label"].map(L.cap_value)
    d["comparison"] = d["comparison"].astype(int)
    vs_auto = {1, 2, 3}
    fig, axs = plt.subplots(3, 3, figsize=(16, 11), sharex=True)
    for i, (m, mlabel) in enumerate(GRID_ROWS):
        for j, team in enumerate(L.TEAMS):
            ax = axs[i, j]
            ax.axhline(0, color="k", lw=0.8)
            sel = d[(d["team"] == team) & ((d["measure"] == m) | ((m == "difference_age_gap_abs") & (d["measure"] == "difference_age_gap_signed")))]
            for _, r in sel.iterrows():
                col = VERDICT_COLOUR.get(r["verdict"], "0.5")
                fixed = r["verdict_route"] == "P2-K"
                if r["comparison"] in vs_auto:
                    mk, dx, ecol = "o", 0.0, col
                elif policy == 2:
                    mk, dx, ecol = "D", 0.012, col
                else:
                    mk, dx, ecol = "s", 0.012, "navy"
                y, lo, hi = r["estimate_mean_of_5"], r["adjusted_ci_low"], r["adjusted_ci_high"]
                ax.errorbar([r["cap"] + dx], [y], yerr=[[y - lo], [hi - y]], fmt="none", ecolor=ecol, capsize=3, lw=1.2)
                ax.plot([r["cap"] + dx], [y], mk, ms=7, markerfacecolor="none" if fixed else col,
                        markeredgecolor="navy" if (policy == 3 and r["comparison"] not in vs_auto) else col, markeredgewidth=1.5)
                if fixed and r["measure"] == "difference_age_gap_signed":
                    ax.annotate("signed", (r["cap"] + dx, y), xytext=(6, 6), textcoords="offset points", fontsize=8)
            ax.set_xlim(0.62, 1.04)
            ax.set_xticks([L.cap_value(c) for c in L.REALISTIC])
            ax.set_xticklabels(L.REALISTIC, rotation=90, fontsize=8)
            if i == 0:
                ax.set_title(f"team {team}")
            if j == 0:
                ax.set_ylabel(mlabel)
            if i == 2:
                ax.set_xlabel("capacity")
    h = [mlines.Line2D([], [], color=c, marker="o", ls="none", label=v) for v, c in VERDICT_COLOUR.items()]
    h.append(mlines.Line2D([], [], color="0.3", marker="o", ls="none", label="against full automation"))
    if policy == 2:
        h.append(mlines.Line2D([], [], color="0.3", marker="D", ls="none", label="team B or C against team A, both at 0.75"))
        h.append(mlines.Line2D([], [], color="0.3", marker="o", markerfacecolor="none", ls="none", label="fixed by construction; not a finding"))
    else:
        h.append(mlines.Line2D([], [], color="0.3", marker="s", markeredgecolor="navy", ls="none", label="against naive review"))
    fig.legend(handles=h, loc="lower center", ncol=len(h), fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    L.savefig(fig, fname)
    plt.show()

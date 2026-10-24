# Section 3.2: the age gap at capacity 0.75, teams B and C: FPR and FNR of each age group under each policy, among the
# alerts (step descriptive, mean of the five versions over the five random orders), with the deciding verdict of
# analyst-aware deferral against naive review on the age gap above each panel (deciding table of step verdicts3). The
# side table of FPRs over every application is removed (round-2 [analyst-35]); those figures are in P3-T10 (section 4.6).
import matplotlib.lines as mlines
fpfn = L.csv("d_fpfn", dtype={"version": str, "team": str, "capacity": str}, keep_default_na=False)
L._ASSERT.check(bool((fpfn["n_legitimate"] >= L.MIN_GROUP).all() and (fpfn["n_frauds"] >= L.MIN_GROUP).all()),
                "every displayed figure over at least 10 applications", panel="P3-F11")
POL = [("full automation", "D"), ("naive review", "s"), ("analyst-aware deferral", "o")]
COL = {"full automation": "0.25", "naive review": "tab:orange", "analyst-aware deferral": "tab:blue"}


def pick(pol, team, grp):
    d = fpfn[(fpfn["policy"] == pol) & (fpfn["age_group"] == grp)]
    d = d if pol == "full automation" else d[(d["team"] == team) & (d["version"] == L.MEAN5)]
    assert len(d) == 1, (pol, team, grp, len(d))
    return d.iloc[0]


dec = DEC3.copy(); dec["comparison"] = dec["comparison"].astype(int)
fig, axs = plt.subplots(1, 2, figsize=(13, 5.4), sharex=True, sharey=True)   # one scale for both teams
for ax, team in zip(axs, ("B", "C")):
    for pol, mk in POL:
        o, y = pick(pol, team, "50 or over"), pick(pol, team, "under 50")
        ax.plot([y["fpr"], o["fpr"]], [y["fnr"], o["fnr"]], "-", color=COL[pol], lw=1.2)
        ax.plot([o["fpr"]], [o["fnr"]], mk, ms=9, color=COL[pol])
        ax.plot([y["fpr"]], [y["fnr"]], mk, ms=9, markerfacecolor="white", markeredgecolor=COL[pol], markeredgewidth=1.6)
    v = dec[(dec["team"] == team) & (dec["measure"] == "difference_age_gap_abs") & (dec["capacity_label"] == "0.75") & (dec["comparison"].isin([5, 6]))]
    assert len(v) == 1, (team, len(v))
    ax.set_title(f"team {team}, capacity 0.75\nanalyst-aware deferral against naive review, size of the age gap:\n"
                 f"deciding verdict: {v.iloc[0]['verdict']}", fontsize=9.5,
                 color={"beats": "tab:green", "does worse": "tab:red"}.get(v.iloc[0]["verdict"], "darkgoldenrod"))
    ax.set_xlabel("FPR among the alerts (wrongly rejected ÷ legitimate)")
axs[0].set_ylabel("FNR among the alerts (frauds accepted ÷ frauds)")
h = [mlines.Line2D([], [], color=COL[p], marker=m, ls="-", label=p) for p, m in POL]
h += [mlines.Line2D([], [], color="0.3", marker="o", ls="none", label="aged 50 or over (filled)"),
      mlines.Line2D([], [], color="0.3", marker="o", markerfacecolor="white", ls="none", label="under 50 (hollow)")]
fig.legend(handles=h, loc="lower center", ncol=5, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.06))
fig.text(0.5, -0.11, "The horizontal distance between a policy's two points is its age gap (FPR₅₀₊ − FPR<₅₀). Average of the five versions and five random orders. "
         "FNR by age group is descriptive, not a measure of the study.", ha="center", fontsize=9)
fig.suptitle("Age gap at capacity 0.75: FPR and FNR of each age group under each policy, teams B and C", y=1.02)
fig.tight_layout(); L.savefig(fig, "P3-F11_fpr_fnr_by_age.png"); plt.show()

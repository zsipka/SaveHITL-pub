# Section 4.6 (round 2): graph P3-F9, team C only (round-2 [analyst-41]); the lines of every team are written to the table file
# as before.
AF = L.csv("p3_access", dtype={"version": str, "capacity_label": str}); AF["capacity_label"] = AF["capacity_label"].map(L.cap_label)
ovf = AF.groupby(["policy", "team", "version", "seed", "capacity_label", "age_group"])[["n_alerts", "n_sent_to_reviewer"]].sum().reset_index().assign(classifier_decision="all")
cf = AF[AF["classifier_decision"] == "confirm"]
F = pd.concat([ovf, cf], ignore_index=True)
F["share"] = share(F["n_sent_to_reviewer"].values, F["n_alerts"].values)
F = F.groupby(["policy", "team", "version", "capacity_label", "age_group", "classifier_decision"])["share"].mean().groupby(["policy", "team", "capacity_label", "age_group", "classifier_decision"]).mean().reset_index()
F["cap"] = F["capacity_label"].map(L.cap_value)
fig, axs = plt.subplots(2, 1, figsize=(9, 9), sharex=True, sharey=True)   # round-2 [analyst-41]: team C only, 2 x 1
team = "C"
for ax, (kind, rowname) in zip(axs, (("all", "All alerts"), ("confirm", "Alerts the classifier would confirm"))):
    for pol, ls in (("policy 3", "-"), ("policy 2", "--")):
        for grp, col in ((OLD, "tab:red"), (YNG, "tab:blue")):
            d = F[(F["policy"] == pol) & (F["team"] == team) & (F["age_group"] == grp) & (F["classifier_decision"] == kind)].sort_values("cap")
            ax.plot(d["cap"], d["share"], ls=ls, color=col, label=V.txt('P3-F9.legend', '{policy}, {group}', {'policy': {'policy 3': 'analyst-aware deferral', 'policy 2': 'naive review'}}, policy=pol, group=grp))
    if kind == "confirm":
        ax.annotate(V.txt('P3-F9.note-zero', '{label} (analyst-aware deferral, 50 or over)', {}, label=L.F9_C_ZERO), xy=(0.5, 0.0), xytext=(0.05, 0.08), fontsize=8, color="tab:red", arrowprops=dict(arrowstyle="->", color="tab:red"))
        ax.text(0.56, 0.16, V.txt('P3-F9.note-policy2-c', '{label}', {}, label=L.F9_P2_C.replace(": ", ":\n", 1).replace("; ", ";\n")), fontsize=8, color="tab:red", transform=ax.transAxes)
    ax.set_title(rowname, fontsize=10)
    ax.set_ylabel('share sent to a reviewer')
axs[1].set_xlabel('capacity')
axs[0].legend(fontsize=8, loc="upper left")
fig.suptitle("Team C: share of alerts sent to a reviewer against capacity, by age group, analyst-aware deferral and naive review", fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.96))
L.savefig(fig, "P3-F9_access_by_age.png"); plt.show()
L.save(F.drop(columns="cap"), "P3-F9_lines.csv")
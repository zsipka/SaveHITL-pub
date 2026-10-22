# Section 6.7: graph P3-F9.
AF = L.csv("p3_access", dtype={"version": str, "capacity_label": str}); AF["capacity_label"] = AF["capacity_label"].map(L.cap_label)
ovf = AF.groupby(["policy", "team", "version", "seed", "capacity_label", "age_group"])[["n_alerts", "n_sent_to_reviewer"]].sum().reset_index().assign(classifier_decision="all")
cf = AF[AF["classifier_decision"] == "confirm"]
F = pd.concat([ovf, cf], ignore_index=True)
F["share"] = share(F["n_sent_to_reviewer"].values, F["n_alerts"].values)
F = F.groupby(["policy", "team", "version", "capacity_label", "age_group", "classifier_decision"])["share"].mean().groupby(["policy", "team", "capacity_label", "age_group", "classifier_decision"]).mean().reset_index()
F["cap"] = F["capacity_label"].map(L.cap_value)
fig, axs = plt.subplots(2, 3, figsize=(16, 8), sharex=True, sharey=True)
for j, team in enumerate(L.TEAMS):
    for i, (kind, rowname) in enumerate((("all", "(i) overall"), ("confirm", "(ii) classifier would confirm"))):
        ax = axs[i, j]
        for pol, ls in (("policy 3", "-"), ("policy 2", "--")):
            for grp, col in ((OLD, "tab:red"), (YNG, "tab:blue")):
                d = F[(F["policy"] == pol) & (F["team"] == team) & (F["age_group"] == grp) & (F["classifier_decision"] == kind)].sort_values("cap")
                ax.plot(d["cap"], d["share"], ls=ls, color=col, label=V.txt('P3-F9.legend', '{policy}, {group}', {'policy': {'policy 3': 'analyst-aware deferral', 'policy 2': 'naive review'}}, policy=pol, group=grp))
        if team == "C" and kind == "confirm":
            ax.annotate(V.txt('P3-F9.note-zero', '{label} (analyst-aware deferral, 50 or over)', {}, label=L.F9_C_ZERO), xy=(0.5, 0.0), xytext=(0.05, 0.08), fontsize=7, color="tab:red", arrowprops=dict(arrowstyle="->", color="tab:red"))
            ax.text(0.30, 0.30, V.txt('P3-F9.note-policy2-c', '{label}', {}, label=L.F9_P2_C.replace("; ", ";\n")), fontsize=7, color="tab:red", transform=ax.transAxes)
        if team == "B":
            ax.text(0.02, 0.78 if kind == "confirm" else 0.92, V.txt('P3-F9.note-b', '{label}', {}, label=L.F9_B_EQUAL), fontsize=7, transform=ax.transAxes)
        ax.set_title(V.txt('P3-F9.panel', 'team {team}: {row}', {}, team=team, row=rowname), fontsize=9)
        if i == 1: ax.set_xlabel('capacity')
        if j == 0: ax.set_ylabel('share sent to a reviewer')
axs[0, 0].legend(fontsize=7, loc="lower right")
fig.suptitle(V.txt('P3-F9.suptitle', 'Share of alerts sent to a reviewer against capacity, by age group, analyst-aware deferral and naive review (average of the five versions, each averaged over the five random orders). {note}', {}, note=L.F9_NOTE), fontsize=10)
L.savefig(fig, "P3-F9_access_by_age.png"); plt.show()
L.save(F.drop(columns="cap"), "P3-F9_lines.csv")
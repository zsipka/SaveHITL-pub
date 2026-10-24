# Section 4.1: table P3-T1, the routing counts by team, version, random order and capacity.
r = ROUT[ROUT["capacity_label"].isin(L.T_CAPS)].copy()
cri = CELLS3[L.lam_eq(CELLS3["lambda"], 0.057) & CELLS3["capacity_label"].isin(L.T_CAPS)][["seed", "team", "version", "capacity_label",
      "criterion_1_share_expert_right_policy_1_wrong", "criterion_1_share_expert_wrong_policy_1_right"]]
cri = cri[cri["team"].isin(["A", "C"])].assign(routing=lambda x: x["team"].map({"A": "AB", "C": "C"})).drop(columns="team")
r = r.merge(cri, on=["routing", "version", "seed", "capacity_label"], how="left")
cols = ["routing", "version", "seed", "router_table", "capacity_label", "K", "load", "n_eligible", "n_reviewed", "n_to_classifier", "n_team_c_test"] + \
       [f"n_slot_{i}" for i in range(10)] + ["ties_experts_tied_resolved_by_fewest", "ties_experts_tied_resolved_by_slot", "ties_best_expert_equal_to_classifier",
       "criterion_1_share_expert_right_policy_1_wrong", "criterion_1_share_expert_wrong_policy_1_right"]
r["capacity_label"] = pd.Categorical(r["capacity_label"], L.T_CAPS, ordered=True)
T1 = r[cols].sort_values(["routing", "capacity_label", "version", "seed"])
L.save(T1, "P3-T1a_routing.csv")   # [analyst-05]: the table is replaced by the two graphs below; its file stays


# [analyst-05], [analyst-41], graph 1: the alerts by the branch of the routing trees, averaged over versions and random orders.
R = ROUT.copy()
R["band_reviewer"] = R["n_reviewed"]
R["band_classifier"] = R["n_classifier_not_beaten"] + np.where(R["routing"] == "C", R["n_team_c_test"], 0)
R["band_pool_full"] = R["n_classifier_pool_full"]
tot = R["band_reviewer"] + R["band_classifier"] + R["band_pool_full"]
L._ASSERT.check(bool((tot == 4457).all()), "graph 1: the three bands add up to 4,457 for every routing, version, random order and capacity",
                n_rows=len(R), n_not_4457=int((tot != 4457).sum()))
BANDS = [("band_reviewer", "routed to a reviewer", "tab:blue"), ("band_classifier", "routed to the classifier", "tab:orange"),
         ("band_pool_full", "pool full", "0.6")]
CAPTION = {"AB": "Routed to the classifier: no reviewer outscores the classifier, counted before the pool is full.\nAfter it, every alert counts as pool full.",
           "C": "Routed to the classifier: alerts of applicants aged 50 or over that the classifier would confirm (team C's rule),\nat any time, "
                "and alerts no reviewer outscores, before the pool is full. After it, every other alert counts as pool full."}
fig, axs = plt.subplots(1, 2, figsize=(14, 5.2), sharey=True)
for ax, (rt, name) in zip(axs, (("AB", "teams A and B (one routing)"), ("C", "team C"))):
    g = R[(R["routing"] == rt) & R["capacity_label"].isin(L.T_CAPS)].groupby("capacity_label")[[b for b, _, _ in BANDS]].mean().reindex(L.T_CAPS)
    bottom = np.zeros(len(g))
    for b, lab, col in BANDS:
        y = 100 * g[b].values / 4457
        ax.bar(range(len(g)), y, bottom=bottom, color=col, label=lab, width=0.6)
        for k, (yy, bb) in enumerate(zip(y, bottom)):
            if yy >= 3:
                ax.text(k, bb + yy / 2, f"{yy:.0f}%", ha="center", va="center", fontsize=8, color="white" if col != "0.6" else "k")
        bottom += y
    ax.set_xticks(range(len(g))); ax.set_xticklabels(L.T_CAPS); ax.set_xlabel("capacity"); ax.set_title(name, fontsize=10)
    ax.text(0.0, -0.2, CAPTION[rt], transform=ax.transAxes, fontsize=8, va="top")
axs[0].set_ylabel("share of the 4,457 alerts, %"); axs[0].legend(fontsize=8, loc="lower left")
fig.suptitle("How analyst-aware deferral allocates the alerts, against capacity (average of the five versions and five random orders)")
fig.tight_layout(); L.savefig(fig, "P3-T1_allocation.png"); plt.show()

# graph 2: each reviewer's share of the reviewed alerts, sorted from largest to smallest; teams A and B (one routing).
slots = [f"n_slot_{i}" for i in range(10)]
fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), sharey=True)
cmap = plt.get_cmap("tab10")
for ax, cap in zip(axs, ("1.00", "0.75")):
    for k, ver in enumerate(L.VERSIONS):
        g = R[(R["routing"] == "AB") & (R["capacity_label"] == cap) & (R["version"] == ver)]
        sh = np.sort(100 * g[slots].values / g["n_reviewed"].values[:, None], axis=1)[:, ::-1]     # per random order, sorted
        x = np.arange(1, 11)
        ax.plot(x, sh.mean(axis=0), "o-", color=cmap(k), ms=4, label=f"version {ver}")
        ax.fill_between(x, sh.min(axis=0), sh.max(axis=0), color=cmap(k), alpha=0.12)
    ax.axhline(10, color="k", ls=":", lw=1, label="even split (10%)")
    ax.set_xticks(range(1, 11)); ax.set_xlabel("reviewer, from the busiest to the least busy"); ax.set_title(f"capacity {cap.replace('1.00', '1')}", fontsize=10)
axs[0].set_ylabel("share of the reviewed alerts, %"); axs[0].legend(fontsize=8)
fig.suptitle("How the reviewed alerts are shared among the ten reviewers, teams A and B (one routing)\n"
             "(line: average of the five random orders; band: their lowest to highest)")
fig.tight_layout(); L.savefig(fig, "P3-T1_reviewer_shares.png"); plt.show()

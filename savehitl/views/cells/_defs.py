# Shared helpers of the notebook's tables and graphs (the study's results-notebook helpers, ported). Executed first in
# every view section, in the namespace that holds L (savehitl.views.lib), V (savehitl.views.show), np, pd, plt, json.
def dec_table(DEC, label, p2k_label=None):
    t = DEC.copy()
    t["measure"] = t["measure"].map(L.mname)
    t["estimate (mean of 5)"] = t["estimate_mean_of_5"]
    t["adjusted interval"] = [f"{L.fmt(lo)} to {L.fmt(hi)}" for lo, hi in zip(t["adjusted_ci_low"], t["adjusted_ci_high"])]
    t["seed range"] = [f"{L.fmt(lo)} to {L.fmt(hi)}" for lo, hi in zip(t["seed_min"], t["seed_max"])]
    t["versions 1 to 5"] = t[[f"v{i}_verdict" for i in range(1, 6)]].astype(str).agg(" / ".join, axis=1)
    t["label"] = [p2k_label if (p2k_label and r == "P2-K") else label for r in t["verdict_route"]]
    return t


def boundary_table(BND, D, comps):
    rows = []
    for _, b in BND[BND["comparison"].isin(comps)].iterrows():
        r = {"comparison": L.COMPARISON_NAMES.get(b["comparison"], b["comparison"]), "team": b["team"], "version": b["version"], "measure": L.mname(b["measure"]),
             "point boundary": b["point_boundary"], "interval summary": b["interval_summary"]}
        dd = D[(D["comparison"] == b["comparison"]) & (D["team"] == b["team"]) & (D["version"] == str(b["version"])) & (D["measure"] == b["measure"]) &
               (D["lambda"].isna() | L.lam_eq(D["lambda"], 0.057))].set_index("capacity_label")
        for c in L.CAP_ORDER:
            if c in dd.index:
                v = dd.at[c, "verdict"]; n = dd.at[c, "deciding_note"]
                r[c] = f"{v}" + (f" ({n})" if isinstance(n, str) and n else "")
        rows.append(r)
    return pd.DataFrame(rows)


def diff_panels(D, BND, comps, measure, title, fname, second_axis=None, pal=None, policy=None):
    pal = pal or {"vs_policy_1": "tab:blue", "vs_policy_2": "tab:red"}
    gap = measure == "difference_age_gap_abs"
    formula = {("vs_policy_1", 2): "naive-auto", ("vs_policy_1", 3): "deferral-auto", ("vs_policy_2", 3): "deferral-naive"}
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.2), sharey=True)
    for ax, team in zip(axs, L.TEAMS):
        ax.axvspan(0.65, 1.0, color="0.92", zorder=0)
        ax.axhline(0, color="k", lw=0.8)
        for comp in comps:
            d = D[(D["comparison"] == comp) & (D["team"] == team) & (D["measure"] == measure) & (D["lambda"].isna() | L.lam_eq(D["lambda"], 0.057))]
            for ver in L.VERSIONS:
                dv = d[d["version"] == ver].sort_values("cap"); ax.plot(dv["cap"], dv["point_estimate"], color=pal[comp], lw=0.6, alpha=0.5)
            dm = d[d["version"] == L.MEAN5].sort_values("cap")
            ax.plot(dm["cap"], dm["point_estimate"], color=pal[comp], lw=2, label=V.txt('diff.legend', '{comparison} (average of the five versions)', {'comparison': {'against policy 1': 'against full automation', 'against policy 2': 'against naive review'}}, comparison=L.COMPARISON_NAMES[comp])
                    + (": " + L.AGE_GAP_FORMULA[formula[(comp, policy)]] if gap and policy else ""))
            ax.fill_between(dm["cap"], dm["ci_low"], dm["ci_high"], color=pal[comp], alpha=0.2)
            b = BND[(BND["comparison"] == comp) & (BND["team"] == team) & (BND["version"].astype(str) == L.MEAN5) & (BND["measure"] == measure)]
            if len(b):
                for x in json.loads(b.iloc[0]["point_boundary_capacities"]):
                    ax.axvline(x, color=pal[comp], ls="--", lw=1)
        if second_axis is not None:
            a2 = ax.twinx(); s = second_axis(team); a2.plot(s["cap"], s["point_estimate"], color="tab:green", ls=":", lw=1.5)
            a2.set_ylabel('overall FPR among the alerts (dotted)', color="tab:green", fontsize=8)
        ax.set_title(V.txt('panel.team', 'team {team}', {}, team=team)); ax.set_xlabel('capacity')
    axs[0].set_ylabel(L.AGE_GAP_FORMULA[formula[(comps[0], policy)]] if gap and policy else V.txt('diff.ylabel', '{measure}', {}, measure=L.mname(measure)))
    axs[0].legend(fontsize=8, loc="best")
    if gap:
        fig.text(0.5, -0.04, L.FPR_DEFINITION, ha="center", fontsize=9)
    fig.suptitle(title); L.savefig(fig, fname); plt.show()


sec2 = lambda team: D2[(D2["comparison"] == "level") & (D2["team"] == team) & (D2["version"] == L.MEAN5) & (D2["measure"] == "overall_false_rejection_rate")].sort_values("cap")
sec3 = lambda team: D3[(D3["comparison"] == "level") & (D3["team"] == team) & (D3["version"] == L.MEAN5) & (D3["measure"] == "overall_false_rejection_rate")].sort_values("cap")


def stacked(D, comp, parts, names, title, fname):
    fig, axs = plt.subplots(1, 3, figsize=(16, 4), sharey=True)
    for ax, team in zip(axs, L.TEAMS):
        base = np.zeros(len(L.CAP_ORDER)); basen = np.zeros(len(L.CAP_ORDER))
        for p_, nm, col in zip(parts, names, ("tab:orange", "tab:purple")):
            d = D[(D["comparison"] == comp) & (D["team"] == team) & (D["version"] == L.MEAN5) & (D["measure"] == p_) & L.lam_eq(D["lambda"], 0.057)].set_index("capacity_label").reindex(L.CAP_ORDER)
            y = d["point_estimate"].fillna(0).values
            ax.bar(range(len(L.CAP_ORDER)), np.where(y > 0, y, 0), bottom=base, color=col, label=nm)
            ax.bar(range(len(L.CAP_ORDER)), np.where(y < 0, y, 0), bottom=basen, color=col)
            base += np.where(y > 0, y, 0); basen += np.where(y < 0, y, 0)
        ax.axhline(0, color="k", lw=0.8); ax.set_xticks(range(len(L.CAP_ORDER))); ax.set_xticklabels(L.CAP_ORDER, rotation=90, fontsize=7)
        ax.set_title(V.txt('panel.team', 'team {team}', {}, team=team)); ax.set_xlabel('capacity')
    axs[0].set_ylabel('misclassification cost, difference'); axs[0].legend(fontsize=8)
    fig.suptitle(title); L.savefig(fig, fname); plt.show()


def indicator_panels(D, specs, title, fname, extra=None):
    fig, axs = plt.subplots(1, len(specs) + (1 if extra else 0), figsize=(4.3 * (len(specs) + (1 if extra else 0)), 3.8))
    for ax, (m, lam) in zip(axs, specs):
        for team, col in zip(L.TEAMS, ("tab:blue", "tab:orange", "tab:green")):
            d = D[(D["comparison"] == "level") & (D["team"] == team) & (D["version"] == L.MEAN5) & (D["measure"] == m)]
            if lam is not None:
                d = d[L.lam_eq(d["lambda"], lam)]
            d = d.sort_values("cap")
            ax.plot(d["cap"], d["point_estimate"], color=col, label=V.txt('legend.team', 'team {team}', {}, team=team)); ax.fill_between(d["cap"], d["ci_low"], d["ci_high"], color=col, alpha=0.15)
        ax.set_title(V.txt('indicator.title-at', '{measure} (cost ratio {lam})', {'measure': {'loss avoided per review, against policy 1': 'loss avoided per review'}}, measure=L.mname(m), lam=lam) if lam else V.txt('indicator.title', '{measure}', {'measure': {'override rate (share of reviewed alerts accepted)': 'share of reviewed alerts overturned', 'subgroup disparity on reviewed alerts': 'age gap on reviewed alerts', 'load (alerts reviewed / K)': 'share of review places used', 'criterion 1: share expert right, policy 1 wrong': 'reviewer right, classifier wrong', 'criterion 1: share expert wrong, policy 1 right': 'reviewer wrong, classifier right'}}, measure=L.mname(m)), fontsize=8)
        ax.set_xlabel('capacity')
    if extra:
        extra(axs[-1])
    axs[0].legend(fontsize=7); fig.suptitle(title); L.savefig(fig, fname); plt.show()


def p2_load(ax):
    d = CELLS2[(CELLS2["team"] == "A") & (CELLS2["version"] == "1") & (CELLS2["seed"] == 1) & L.lam_eq(CELLS2["lambda"], 0.057) & (CELLS2["K"] > 0)].copy()
    d["cap"] = d["capacity_label"].map(L.cap_value); d = d.sort_values("cap")
    ax.plot(d["cap"], d["load_one_over_capacity"], "k"); ax.set_title('alerts per review place (1 ÷ capacity, all teams)', fontsize=8); ax.set_xlabel('capacity'); ax.set_yscale("log")


def verdict_grid(CL, title, fname):
    lams = ["0.035", "0.0537", "0.057", "0.171"]; code_ = {"beats": 1, "no difference shown": 0, "does worse": -1}
    fig, axs = plt.subplots(1, 3, figsize=(17, 2.8))
    for ax, team in zip(axs, L.TEAMS):
        d = CL[(CL["team"] == team) & (CL["version"].astype(str) == L.MEAN5)].set_index("capacity_label").reindex(L.CAP_ORDER)
        M = np.array([[code_.get(d.at[c, f"verdict_{l}"], np.nan) for c in L.CAP_ORDER] for l in lams])
        ax.imshow(M, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        ax.set_yticks(range(4)); ax.set_yticklabels(lams); ax.set_xticks(range(22)); ax.set_xticklabels(L.CAP_ORDER, rotation=90, fontsize=7)
        ax.set_title(V.txt('panel.team', 'team {team}', {}, team=team)); ax.set_xlabel('capacity')
    axs[0].set_ylabel('cost ratio')
    fig.suptitle(title + '  (green: beats; yellow: no difference shown; red: does worse)', y=1.1); L.savefig(fig, fname); plt.show()


def add_u_label(t, CL, name):
    # the P-U label of the verdict run, its own column, copied from the run's `label` column, joined on team, version and capacity
    k = ["team", "version", "capacity_label"]
    t[name] = t[k].merge(CL[k + ["label"]], how="left", on=k, validate="one_to_one")["label"].values


def show_u_label(t, name, key, view):
    V.say('ulabel.caption', "{name}: how each team's result holds across cost ratios (average of the five versions; rows: team; columns: capacity; empty: the team beats full automation at none of the other cost ratios)", {'name': {'P2-U label': 'Naive review', 'P3-U label': 'Analyst-aware deferral'}}, name=name, run="")
    V.show(t.pivot(index="team", columns="capacity_label", values=name).reindex(index=L.TEAMS, columns=L.CAP_ORDER).fillna(""), **view)


def chance(CH, title, fname, view):
    r = CH.iloc[0]
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.bar([0, 1], [r["n_beats"], r["n_does_worse"]], color=["tab:green", "tab:red"], label='observed')
    ax.plot([-0.4, 1.4], [r["expected_each_side"]] * 2, "k--", label=V.txt('chance.expected', 'expected by chance ({e:.1f} each side)', {}, e=r["expected_each_side"]))
    ax.set_xticks([0, 1]); ax.set_xticklabels(['beats', 'does worse']); ax.legend(fontsize=8)
    ax.set_title(title + V.txt('chance.title', ' ({n:,} descriptive ranges)', {}, n=int(r["n_intervals"])), fontsize=9); L.savefig(fig, fname); plt.show()
    V.show(CH, **view)


def forest(T, title, fname, row):
    # row: (key, template, field maps) of the row label, from the item cell (forest.row-p2, forest.row-p3): the two policies number their comparisons differently
    ms = list(dict.fromkeys(T["measure"]))
    fig, axs = plt.subplots(len(ms), 1, figsize=(10, len(ms) * (0.26 * max(T.groupby("measure").size()) + 1.2)))
    for ax, m in zip(np.atleast_1d(axs), ms):
        g = T[T["measure"] == m].reset_index(drop=True)
        y = np.arange(len(g))[::-1]
        ax.errorbar(g["estimate_mean_of_5"], y, xerr=[g["estimate_mean_of_5"] - g["adjusted_ci_low"], g["adjusted_ci_high"] - g["estimate_mean_of_5"]], fmt="s", color="k", capsize=2)
        for i in range(1, 6):
            ax.plot(g[f"v{i}_estimate"], y, ".", color="tab:blue", alpha=0.6)
        ax.axvline(0, color="r", lw=0.8)
        ax.set_yticks(y); ax.set_yticklabels([V.txt(*row, comparison=c, team=t, capacity=k, verdict=v)
                                              for c, t, k, v in zip(g["comparison"], g["team"], g["capacity_label"], g["verdict"])], fontsize=7)
        ax.set_title(V.txt('forest.panel', '{measure}', {}, measure=m), fontsize=9)
    fig.suptitle(title, y=1.0); fig.tight_layout(); L.savefig(fig, fname); plt.show()


OLD, YNG = "50 or over", "under 50"


def keyed_rows(key, keys):
    # Rows of the run's own descriptive export, selected by their key columns (comparison, version, team, capacity_label,
    # lambda, measure); exactly one row per key, else the step stops. Nothing is computed: texts as written, the three
    # figures read as numbers, the measure's full name added.
    raw = L.csv(key, dtype=str, keep_default_na=False)
    raw["capacity_label"] = raw["capacity_label"].map(lambda s: s if " vs " in str(s) else L.cap_label(s))
    cols = ["comparison", "version", "team", "capacity_label", "lambda", "measure"]
    rows = []
    for k in keys:
        m = raw
        for c, want in zip(cols, k):
            m = m[m[c] == want]
        assert len(m) == 1, f"{key}: key {k}: {len(m)} rows, not one"
        rows.append(m.iloc[0])
    t = pd.DataFrame(rows).reset_index(drop=True)
    t["comparison name"] = t["comparison"].map(lambda c: L.COMPARISON_NAMES.get(c, c))
    t["measure name"] = t["measure"].map(L.mname)
    t["lambda"] = [None if x == "" else x for x in t["lambda"]]
    for c in ("point_estimate", "ci_low", "ci_high"):
        t[c] = [float(x) for x in t[c]]           # Python's float(): the number the written text denotes, exactly
    return t[["comparison name", "team", "capacity_label", "lambda", "measure name", "point_estimate", "ci_low", "ci_high", "verdict"]]


def share(n_sent, n):
    return np.where(n > 0, n_sent / np.where(n > 0, n, 1), np.nan)


def t9_view(team, version=L.MEAN5):
    v = T9[(T9["team"] == team) & (T9["version"] == version)].copy()
    v["share, 50 or over"] = [L.T9_NOT_DEFINED if np.isnan(x) else f"{x:.4f}" for x in v[f"share_mean [{OLD}]"]]
    v["share, under 50"] = [L.T9_NOT_DEFINED if np.isnan(x) else f"{x:.4f}" for x in v[f"share_mean [{YNG}]"]]
    v["counts, 50 or over (sent / alerts x routings)"] = [f"{int(s):,} / ({int(n):,} x {int(k)})" for s, n, k in zip(v[f"n_sent_pooled [{OLD}]"], v[f"n_alerts [{OLD}]"], v[f"routings_pooled [{OLD}]"])]
    v["counts, under 50 (sent / alerts x routings)"] = [f"{int(s):,} / ({int(n):,} x {int(k)})" for s, n, k in zip(v[f"n_sent_pooled [{YNG}]"], v[f"n_alerts [{YNG}]"], v[f"routings_pooled [{YNG}]"])]
    v["difference (percentage points)"] = [L.T9_NOT_DEFINED if np.isnan(x) else f"{x:+.2f}" for x in v["difference, percentage points (50 or over minus under 50)"]]
    if version != L.MEAN5:
        v["seed range, 50 or over"] = [f"{a_:.4f} to {b_:.4f}" for a_, b_ in zip(v[f"share_seed_low [{OLD}]"], v[f"share_seed_high [{OLD}]"])]
        v["seed range, under 50"] = [f"{a_:.4f} to {b_:.4f}" for a_, b_ in zip(v[f"share_seed_low [{YNG}]"], v[f"share_seed_high [{YNG}]"])]
    cols = ["capacity_label", "share kind", "policy", "share, 50 or over", "share, under 50", "difference (percentage points)", "counts, 50 or over (sent / alerts x routings)",
            "counts, under 50 (sent / alerts x routings)"] + (["seed range, 50 or over", "seed range, under 50"] if version != L.MEAN5 else []) + ["cell labels"]
    return v[cols]

# ------------------------------------------------------------------ section 6.5: verdict colour grid and generated ranges
GRID_MEASURES = [("difference_expected_loss", "misclassification cost"), ("difference_accepted_frauds", "frauds accepted"),
                 ("difference_age_gap_abs", "the size of the age gap")]
VERDICT_CODE = {"beats": 1, "no difference shown": 0, "does worse": -1}


def verdict_of(cell):
    """The verdict text of a boundary-table cell ("beats (deciding verdict …)" -> "beats"); None if empty."""
    if not isinstance(cell, str) or not cell:
        return None
    for v in VERDICT_CODE:
        if cell == v or cell.startswith(v + " ("):
            return v
    return None


def cap_word(c):
    return "1" if c == "1.00" else c


def ranges_text(caps):
    """[analyst-42]: contiguous ranges of the 22-point grid, in increasing order, joined by "and"."""
    idx = sorted(L.CAP_ORDER.index(c) for c in caps)
    if len(idx) == len(L.CAP_ORDER):
        return "at every capacity"
    if idx == list(range(1, len(L.CAP_ORDER))):
        return "at every capacity above 0"
    runs, cur = [], [idx[0]]
    for i in idx[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            runs.append(cur); cur = [i]
    runs.append(cur)
    parts = [f"at {cap_word(L.CAP_ORDER[r[0]])}" if len(r) == 1 else f"from {cap_word(L.CAP_ORDER[r[0]])} to {cap_word(L.CAP_ORDER[r[-1]])}" for r in runs]
    return " and ".join(parts)


def range_sentence(v, comp_label, policy_name, against, measure, short):
    """One sentence per measure and comparison, from the verdict at each capacity (average of the five versions)."""
    clauses = []
    for k, team in enumerate(L.TEAMS):
        row = v[(v["comparison"] == comp_label) & (v["team"] == team) & (v["measure"] == L.mname(measure))]
        assert len(row) == 1, (comp_label, team, measure, len(row))
        row = row.iloc[0]
        by = {"beats": [], "does worse": []}
        for c in L.CAP_ORDER:
            w = verdict_of(row.get(c))
            if w in by:
                by[w].append(c)
        bits = []
        if by["beats"]:
            bits.append(("beats " + against if k == 0 else "beats") + f" with team {team} " + ranges_text(by["beats"]) if k == 0 else "beats " + ranges_text(by["beats"]))
        if by["does worse"]:
            if k == 0 and not bits:
                bits.append(f"does worse than {against} with team {team} " + ranges_text(by["does worse"]))
            else:
                bits.append("does worse " + ranges_text(by["does worse"]))
        if not bits:
            bits.append(f"shows no difference from {against} with team {team} at any capacity" if k == 0 else "shows no difference at any capacity")
        clauses.append(" and ".join(bits) if k == 0 else f"with team {team}, it " + " and ".join(bits))
    return f"On {short}, {policy_name} " + "; ".join(clauses) + ". Elsewhere no difference is shown."


def cap_position(x):
    """Position of a capacity value on the 22-point grid's index axis (linear between neighbouring points)."""
    vals = [L.cap_value(c) for c in L.CAP_ORDER]
    return float(np.interp(float(x), vals, range(len(vals))))


def verdict_colour_grid(T4, BND, comps, title, fname):
    """[analyst-07]: the descriptive verdict at each capacity (average of the five versions), one panel per measure, one row per
    team (and comparison), capacity across, the realistic range shaded, a tick where the average difference crosses zero."""
    from matplotlib.colors import ListedColormap
    import matplotlib.patches as mpatches
    v = T4[T4["version"] == L.MEAN5]
    rows = [(c, t) for c in comps for t in L.TEAMS]
    cname = {c: L.COMPARISON_NAMES[c] for c in comps}
    cmap = ListedColormap(["tab:red", "gold", "tab:green"])
    fig, axs = plt.subplots(len(GRID_MEASURES), 1, figsize=(15, 0.5 * len(rows) * len(GRID_MEASURES) + 2.6))
    for ax, (m, short) in zip(axs, GRID_MEASURES):
        M = np.full((len(rows), len(L.CAP_ORDER)), np.nan)
        for i, (c, t) in enumerate(rows):
            r = v[(v["comparison"] == cname[c]) & (v["team"] == t) & (v["measure"] == L.mname(m))]
            assert len(r) == 1, (c, t, m)
            r = r.iloc[0]
            for j, cap in enumerate(L.CAP_ORDER):
                w = verdict_of(r.get(cap))
                M[i, j] = VERDICT_CODE[w] if w else np.nan
            b = BND[(BND["comparison"] == c) & (BND["team"] == t) & (BND["version"].astype(str) == L.MEAN5) & (BND["measure"] == m)]
            if len(b):
                for x in json.loads(b.iloc[0]["point_boundary_capacities"]):
                    ax.plot([cap_position(x)], [i], marker="|", ms=16, mew=2.5, color="k")
        ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=-1, vmax=1, aspect="auto")
        ax.axvspan(L.CAP_ORDER.index("0.65") - 0.5, len(L.CAP_ORDER) - 0.5, ymin=0, ymax=1, facecolor="none", edgecolor="k", lw=1.5, hatch="")
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([f"team {t}" + ("" if len(comps) == 1 else ", " + {"vs_policy_1": "against full automation", "vs_policy_2": "against naive review"}[c])
                            for c, t in rows], fontsize=8.5)
        ax.set_xticks(range(len(L.CAP_ORDER))); ax.set_xticklabels([cap_word(c) for c in L.CAP_ORDER], rotation=90, fontsize=8)
        ax.set_title(short, fontsize=10, loc="left")
    axs[-1].set_xlabel("capacity (realistic range 0.65 to 1 framed)")
    h = [mpatches.Patch(color=c, label=l) for l, c in (("beats", "tab:green"), ("no difference shown", "gold"), ("does worse", "tab:red"))]
    h.append(plt.Line2D([], [], color="k", marker="|", ms=12, mew=2.5, ls="none", label="the average difference crosses zero"))
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=(0, 0.03, 1, 1)); L.savefig(fig, fname); plt.show()

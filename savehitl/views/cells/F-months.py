# The data and the set-up: which months the study uses, and for what. The lanes are fixed from the framework's code and
# the study's design (framework models reference, rows 1, 3, 4(a); Code/alert_model/training_and_predicting.py:54-56, 64,
# 73, 77; Code/classifier_h/training.py:36-37; Code/expert_models/run_ova.py:36-45); only the alert counts in the header
# are computed, from the alerts file (step applications).
import matplotlib.patches as mpatches
am = L.csv("a_month")
ROLE = {"train": ("learns from the labels (training)", "#4c72b0"), "choose": ("settings, cut-off or model chosen", "#dd8452"),
        "param": ("reviewer parameters set", "#8172b3"), "score": ("scores or decides (no learning)", "#c7c7c7"),
        "every": ("reviewers' decision on every alert", "#64b5cd"), "result": ("results measured", "#55a868")}
# lane -> list of (month, role, half): half "" = whole cell, "top"/"bottom" = the cell holds two roles
LANES = [
    ("Alert Model\n(as shipped)", [(0, "train", ""), (1, "train", ""), (2, "train", ""), (3, "choose", "top"), (3, "score", "bottom"),
                                   (4, "score", ""), (5, "score", ""), (6, "score", ""), (7, "score", "")]),
    ("Classifier h\n(as shipped)", [(3, "train", ""), (4, "train", ""), (5, "train", ""), (6, "choose", ""), (7, "score", "")]),
    ("50 reviewers\n(generated)", [(m, "param", "top") for m in (3, 4, 5, 6)] + [(m, "every", "bottom") for m in (3, 4, 5, 6)] + [(7, "every", "")]),
    ("router, 250 models\n(trained)", [(3, "train", ""), (4, "train", ""), (5, "train", ""), (6, "choose", ""), (7, "score", "")]),
    ("results", [(7, "result", "")]),
]
fig, ax = plt.subplots(figsize=(13, 4.6))
nl = len(LANES)
ax.axvspan(6.5, 7.5, color="#fff2cc", zorder=0)
for i, (lane, cells) in enumerate(LANES):
    y = nl - 1 - i
    for m, role, half in cells:
        h, y0 = (0.8, y - 0.4) if not half else (0.4, y if half == "top" else y - 0.4)
        ax.add_patch(mpatches.Rectangle((m - 0.45, y0), 0.9, h, color=ROLE[role][1], ec="white", lw=1, zorder=2))
ax.tick_params(axis="both", length=0)
ax.set_yticks(range(nl)); ax.set_yticklabels([l for l, _ in LANES][::-1], fontsize=9)
ax.set_xticks(range(8)); ax.set_xticklabels([f"month {m}" for m in range(8)], fontsize=9)
ax.set_xlim(-0.6, 7.6); ax.set_ylim(-0.6, nl + 0.15)
for _, r in am.iterrows():
    ax.text(r["month"], nl - 0.35, "no alerts" if r["n_alerts"] == 0 else f"{int(r['n_alerts']):,} alerts", ha="center", fontsize=8.5)
ax.text(7, -0.55, "test month", ha="center", fontsize=9, fontweight="bold")
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.legend(handles=[mpatches.Patch(color=c, label=t) for t, c in ROLE.values()], loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8.5, frameon=False)
ax.set_title("Which months the study uses, and for what")
fig.text(0.42, -0.02, "Nothing is learned, chosen or set on month 7.", ha="center", fontsize=9.5)
L.savefig(fig, "F-months_months_used.png"); plt.show()

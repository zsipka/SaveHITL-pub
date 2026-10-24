# Section 6.1: graph P1-F1, the three measures against the cost ratio.
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
spec = [("expected_loss_total", 'expected loss (total)'), ("regulatory_exposure_accepted_frauds_count", 'regulatory exposure (accepted frauds)'),
        ("fairness_exposure_age_gap", 'fairness exposure (age gap; FPR among the alerts)')]
for a_, (m, title) in zip(ax, spec):
    for pol, st in (("policy_1", "-o"), ("confirm_every_alert", "--s")):
        d = p1[(p1["policy"] == pol) & (p1["measure"] == m)].sort_values("lambda")
        a_.errorbar(d["lambda"], d["value"], yerr=[d["value"] - d["ci95_low"], d["ci95_high"] - d["value"]], fmt=st, capsize=3,
                    label={"policy_1": 'full automation', "confirm_every_alert": 'confirm every alert (reference)'}[pol])
    a_.axvline(0.057, color="grey", ls=":", label='main cost ratio 0.057')
    a_.set_xlabel('cost ratio'); a_.set_title(title); a_.set_xscale("log")
ax[0].legend(fontsize=8)
fig.suptitle('Full automation and "confirm every alert": the three measures against the cost ratio')
L.savefig(fig, "P1-F1_measures_vs_cost_ratio.png"); plt.show()
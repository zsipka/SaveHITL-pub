"""The rework of the notebook (intermediate review version): the aggregate figures' safeguards, the generated capacity
ranges, the display terminology, and the notebook's structure."""
import json
import os
import re

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS = os.path.join(ROOT, "savehitl", "views", "cells")


def _nb():
    return json.load(open(os.path.join(ROOT, "savehitl_results.ipynb"), encoding="utf-8"))


def _defs():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from savehitl.views import lib as L, show as V
    ns = {"L": L, "V": V, "np": np, "pd": pd, "plt": plt, "json": json, "os": os}
    exec(compile(open(os.path.join(CELLS, "_defs.py"), encoding="utf-8").read(), "_defs.py", "exec"), ns)
    return ns


def test_small_edge_group_is_merged_towards_the_middle():
    from savehitl.steps.applications import merge_small
    counts = {10: 500, 20: 900, 30: 800, 80: 40, 90: 4}
    g = merge_small(counts, [10, 20, 30, 80, 90], lambda k: str(k))
    assert g[-1] == ("80 and over", [80, 90]) and all(sum(counts[k] for k in keys) >= 10 for _, keys in g)
    g = merge_small({10: 3, 20: 50, 30: 50}, [10, 20, 30], lambda k: str(k))
    assert g[0] == ("20 and under", [10, 20])
    assert merge_small({10: 50, 20: 50}, [10, 20], str) == [("10", [10]), ("20", [20])]


def test_missing_value_codes_as_the_datasheet_declares():
    from savehitl.steps.applications import MISSING, missing_mask
    assert set(MISSING) == {"prev_address_months_count", "current_address_months_count", "intended_balcon_amount", "bank_months_count",
                            "session_length_in_minutes", "device_distinct_emails_8w"}
    v = np.array([-1, 0, 5, -3])
    assert missing_mask("bank_months_count", v).tolist() == [True, False, False, False]
    assert missing_mask("intended_balcon_amount", v).tolist() == [True, False, False, True]
    assert missing_mask("velocity_6h", v).tolist() == [False] * 4        # not declared by the datasheet: kept as values


def test_spearman_pairwise_leaves_missing_out_pair_by_pair():
    from scipy.stats import spearmanr
    from savehitl.steps.applications import spearman_pairwise
    rng = np.random.RandomState(0)
    x = rng.rand(200); y = x + rng.rand(200); b = rng.randint(0, 30, 200).astype(float)
    b[:40] = -1
    df = pd.DataFrame({"fraud_bool": x, "bank_months_count": b, "income": y})
    r = spearman_pairwise(df, ["fraud_bool", "bank_months_count", "income"], None).set_index(["row", "column"])
    assert abs(r.at[("income", "fraud_bool"), "spearman"] - spearmanr(x, y).correlation) < 1e-12
    m = b != -1
    assert abs(r.at[("bank_months_count", "fraud_bool"), "spearman"] - spearmanr(b[m], x[m]).correlation) < 1e-12
    assert r.at[("bank_months_count", "fraud_bool"), "n_applications"] == 160


def test_capacity_ranges_follow_the_fixed_form():
    ns = _defs()
    rt = ns["ranges_text"]
    assert rt(["0.40"]) == "at 0.40"
    assert rt(["0.30", "0.35", "0.40"]) == "from 0.30 to 0.40"
    assert rt(["0.95", "1.00"]) == "from 0.95 to 1"
    assert rt([c for c in ns["L"].CAP_ORDER[1:]]) == "at every capacity above 0"
    assert rt(["0.10", "0.15", "0.90", "10/11"]) == "from 0.10 to 0.15 and from 0.90 to 10/11"


def test_range_sentence_lists_each_team_and_reads_no_difference():
    ns = _defs()
    L = ns["L"]
    m = L.mname("difference_expected_loss")
    rows = []
    for team, beats in (("A", ["0.50", "0.55"]), ("B", []), ("C", ["1.00"])):
        r = {"comparison": "against policy 1", "team": team, "version": L.MEAN5, "measure": m}
        for c in L.CAP_ORDER:
            r[c] = "beats (deciding verdict: x)" if c in beats else "no difference shown"
        rows.append(r)
    s = ns["range_sentence"](pd.DataFrame(rows), "against policy 1", "naive review", "full automation", "difference_expected_loss", "misclassification cost")
    assert s == ("On misclassification cost, naive review beats full automation with team A from 0.50 to 0.55; with team B, it shows no "
                 "difference at any capacity; with team C, it beats at 1. Elsewhere no difference is shown.")


def test_display_terminology_is_display_only():
    from savehitl.views import lib as L, show as V
    assert L.display_text("expected loss, difference") == "misclassification cost, difference"
    assert L.display_text("overall false rejection rate") == "overall FPR"
    assert L.display_text("false rejections aged 50 or over (count)") == "FP among applicants aged 50 or over (count)"
    df = pd.DataFrame({"expected loss": ["false rejection rate"]})
    v = V._display_terms(df)
    assert list(v.columns) == ["misclassification cost"] and v.iat[0, 0] == "FPR"
    assert list(df.columns) == ["expected loss"] and df.iat[0, 0] == "false rejection rate"     # the original is unchanged
    assert L.MEASURE_NAMES["difference_expected_loss"] == "expected loss, difference"            # names written to tables/ unchanged


def test_figure_texts_take_the_display_terminology():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from savehitl.views import lib as L
    fig, ax = plt.subplots()
    ax.set_ylabel("expected loss, difference"); ax.set_title("overall false rejection rate")
    L.retext_figure(fig)
    assert ax.get_ylabel() == "misclassification cost, difference" and ax.get_title() == "overall FPR"
    plt.close(fig)


def test_notebook_structure_of_the_rework():
    cells = _nb()["cells"]
    md = [c for c in cells if c["cell_type"] == "markdown"]
    text = "\n".join("".join(c["source"]) for c in md)
    for bad in ("Propose to replace", "[analyst-", "[owner-", "S2-D-", "DQ-", "R2-", "[[", "(its own cell)", "## The heavy steps",
                "What a re-run gives"):
        assert bad not in text, bad
    src = ["".join(c["source"]) for c in cells]
    i = src.index('nb.section("F-data")')
    assert src[i - 1].startswith("These figures summarise FiFAR's `Base.csv` in aggregate")          # legal's sentence directly above
    for item in ("P2-F10", "P3-F10"):
        assert "Heavy step" in src[src.index(f'nb.section("{item}")') - 1]
    anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
    for c in md:
        lines = "".join(c["source"]).split("\n")
        for k, line in enumerate(lines):
            if line.startswith("## ") and line != "## Contents":
                assert k > 0 and lines[k - 1].startswith('<a id="'), line
    for link in re.findall(r"\]\(#([^)]+)\)", text):
        assert link in anchors, link
    assert 'nb.section("P3-T8")' not in src                       # withdrawn from the notebook; its file is still written

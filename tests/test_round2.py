"""Round 2 of the notebook rework: the two notebooks (short and long) run the same computation and write the same
files; the long one is the short one plus the Appendix; items shown in two places display only their own part; the
"not run again" lines are no longer printed."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cells(name):
    return json.load(open(os.path.join(ROOT, name), encoding="utf-8"))["cells"]


def _src(c):
    return "".join(c["source"]) if isinstance(c["source"], list) else c["source"]


def _items(cells):
    out = []
    for c in cells:
        if c["cell_type"] == "code":
            out += re.findall(r'nb\.section\("([^"]+)"\)', _src(c))
    return out


def test_long_is_short_plus_appendix():
    short, long_ = _cells("savehitl_results.ipynb"), _cells("savehitl_results_long.ipynb")
    s = [c for c in short if c["id"] != "r2-files"]                     # the short notebook's files cell
    toc_s, toc_l = s[1], long_[1]
    assert toc_s["id"] == toc_l["id"] == "rw-toc"
    assert _src(toc_l) == _src(toc_s).replace("- [5. Limitations and risks](#5-limitations-and-risks)\n",
                                               "- [5. Limitations and risks](#5-limitations-and-risks)\n- [Appendix](#appendix)\n")
    rest_s, rest_l = s[2:], long_[2:]
    k = [c["id"] for c in rest_l].index("r2-appendix")
    t = [c["id"] for c in rest_l].index("c126")                          # the technical section
    assert rest_l[:k] + rest_l[t:] == rest_s                             # identical cells, in the same order
    assert all(_src(c).count("### A.") <= 1 for c in rest_l[k:t])


def test_both_notebooks_write_the_same_files():
    from savehitl.views.sections import NOT_SHOWN_IN_SHORT, ITEMS
    short, long_ = _cells("savehitl_results.ipynb"), _cells("savehitl_results_long.ipynb")
    files = [c for c in short if c["id"] == "r2-files"]
    assert len(files) == 1
    written = re.findall(r'"([^"]+)"', _src(files[0]).split("nb.write_files(", 1)[1])
    assert written == NOT_SHOWN_IN_SHORT
    cell_of = lambda items: {c for i in items for c in ITEMS[i]["cells"]}
    # every view cell the long notebook runs is run by the short one too (shown, or written without display)
    assert cell_of(_items(long_)) == cell_of(_items(short) + written)
    assert not set(written) & set(_items(short))


def test_items_shown_in_two_places_display_only_their_part():
    from savehitl.views.sections import ITEMS
    for g, t in (("P2-T4", "P2-T4-tables"), ("P3-T4", "P3-T4-tables"), ("P2-F5", "P2-F5-table"), ("P2-F7", "P2-F7-tables"), ("P3-F6", "P3-F6-tables")):
        assert ITEMS[g]["part"] == "graph" and ITEMS[t]["part"] == "tables" and ITEMS[g]["cells"] == ITEMS[t]["cells"]
        src = open(os.path.join(ROOT, "savehitl", "views", "cells", ITEMS[g]["cells"][0] + ".py"), encoding="utf-8").read()
        assert "L.save(" in src.split("if PART")[0] or src.rstrip().split("\n")[-1].startswith("L.save(")   # written by both parts
    short = _items(_cells("savehitl_results.ipynb"))
    assert not any(i.endswith(("-tables", "-table")) for i in short)


def test_done_steps_print_nothing(tmp_path, capsys):
    from savehitl import runner
    L = runner.Layout(str(tmp_path), python="python")
    out = os.path.join(L.outputs, "draw")
    os.makedirs(out)
    open(os.path.join(out, "_done.json"), "w").write("{}")
    assert runner.run_step(L, "draw", "draw") == out
    assert capsys.readouterr().out == ""                                 # round-2 [analyst-34]
    assert "not run again" in open(os.path.join(L.logs, "run_log.jsonl")).read()     # still recorded in the run's log


def test_short_notebook_section_order_and_texts():
    text = "\n".join(_src(c) for c in _cells("savehitl_results.ipynb") if c["cell_type"] == "markdown")
    heads = re.findall(r"^(#{2,3} .+)$", text, flags=re.M)
    want = ["## 1. Running the notebook", "## 2. The data and the set-up", "## 3. Hypothesis", "### 3.1", "### 3.2", "### 3.3",
            "## 4. Descriptive results", "### 4.1", "### 4.2", "### 4.3", "### 4.4", "### 4.5", "### 4.6", "### 4.7", "### 4.8", "### 4.9",
            "## 5. Limitations and risks", "### 5.1 Limitations", "### 5.2 Risks"]
    got = [h for h in heads if not h.startswith("## Contents")][:len(want)]
    assert all(g.startswith(w) for g, w in zip(got, want)), got
    for gone in ("Reading to follow", "section 6.", "section 8.", "sections 6.", "(section 7)", "(section 5)", "#6-risk-measures",
                 "#8-3-the-full-sweep", "a small table beside it"):
        assert gone not in text, gone

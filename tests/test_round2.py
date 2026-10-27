"""Round 2 of the notebook rework: the two notebooks (short and long) run the same computation and write the same
files, except the months graph, which only the long one shows and writes; the long one is the short one plus the
months graph and the Appendix; items shown in two places display only their own part; the "not run again" lines are
no longer printed."""
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


TECH_TOC = ("- [The switch in this run](#the-switch-in-this-run)\n- [Input checksums](#input-checksums)\n"
            "- [Map from each item to its design identifier](#map-from-each-item-to-its-design-identifier)\n- [Label texts](#label-texts)\n"
            "- [The results that decide, in full](#the-results-that-decide-in-full)\n- [Boundary summaries: caveat](#boundary-summaries-caveat)\n"
            "- [Run time and memory of this run](#run-time-and-memory-of-this-run)\n- [This run's outputs in one archive](#this-runs-outputs-in-one-archive)")
# Round 5 ([owner-18] cut, [analyst-51]): the short notebook stands alone and names no other notebook, and the months
# graph is in the long notebook only. So four cells above its thick line, two cells of section 2 and the map read
# differently. These are the short notebook's only text differences from the long notebook's shared cells (pairs of
# short text, long text, applied in order).
_MAP_FILE_ONLY = {"3": "A.2", "9": "A.1", "10": "A.1", "11": "A.2", "13": "A.2", "14": "A.3", "15": "A.3", "16": "A.4",
                  "17": "A.4", "21": "A.6", "22": "A.7", "26": "A.8", "29": "A.10", "30": "A.10", "31": "A.11", "32": "A.11"}
_MAP_SHOWN = {"18": ("4.1", "table", "A.5"), "19": ("4.1", "table", "A.5"), "20": ("4.6", "table", "A.6"),
              "24": ("4.9", "tables", "A.8"), "25": ("4.9", "table", "A.8")}
SHORT_ONLY_TEXT = {
    "c000": [("Technical records are not needed to read the results: the set-up in [section 1](#1-running-the-notebook) "
              "checks every input file against its listed checksum and stops if any differs, and run time and memory are "
              "covered in [section 5.2](#52-risks).",
              "Technical records (run time and memory of this run, input checksums, and how each item traces to the "
              "study's design) are at the end and are not needed to read the results.")],
    "c109": [("(7.84 against 37.52, averaged over the five versions, a ratio of 0.21; `tables/P2-T3_deciding_results.csv`)",
              "(0.21; long notebook, A.9)")],
    "c125": [("The run records each step's run time and, after the set-up, its peak memory in its folder `logs/`; the README "
              "gives the run time and memory of the Colab runs ([README, \"Google Colab (the tested route)\"]"
              "(https://github.com/zsipka/SaveHITL-pub#google-colab-the-tested-route)).",
              "Run time and memory are in the technical section.")],
    "c126": [("# Technical section\n\n" + TECH_TOC + "\n\n", "# Technical section\n\n")],
    "rw-data-intro": [("(file `Base.csv`). Months are numbered 0 to 7, as in the data files. The dataset's", "(file `Base.csv`). The dataset's")],
    "c131": [(" A section reading \"not shown (file only)\" marks an item the notebook writes to file, in the last code cell of "
              "section 4.9, without showing it.", ""),
             ("|---|---|---|---|---|\n| 0b |",
              "|---|---|---|---|---|\n| 0a | 2 | Which months the study uses, and for what | F-months (new) | `figures/F-months_months_used.png` |\n| 0b |")]
            + [(f"\n| {r} | not shown (file only) |", f"\n| {r} | {a} (long notebook) |") for r, a in _MAP_FILE_ONLY.items()]
            + [(f"\n| {r} | {s} (its table: file only) |", f"\n| {r} | {s}; {w} {a} (long notebook) |") for r, (s, w, a) in _MAP_SHOWN.items()],
    "rw-heavy-data": [("The next code cell computes the aggregate figures of `Base.csv` (1,000,000 applications), which the graph of this section reads.",
                       "The next cell computes the aggregate figures of `Base.csv` (1,000,000 applications), which both graphs of this section read.")],
}


def test_long_is_short_plus_appendix():
    short, long_ = _cells("savehitl_results.ipynb"), _cells("savehitl_results_long.ipynb")
    s = [c for c in short if c["id"] not in ("r2-files", "r5-thick-line")]   # the short notebook's files cell and its thick line
    toc_s, toc_l = s[1], long_[1]
    assert toc_s["id"] == toc_l["id"] == "rw-toc"
    assert _src(toc_s).endswith("- [5. Limitations and risks](#5-limitations-and-risks)")      # sections 1 to 5 only
    assert _src(toc_l) == _src(toc_s) + "\n- [Appendix](#appendix)\n" + TECH_TOC
    LONG_ONLY = ("rw-months-text", "rw-item-months")                     # the months graph and its text: long notebook only
    rest_s, rest_l = s[2:], [c for c in long_[2:] if c["id"] not in LONG_ONLY]
    k = [c["id"] for c in rest_l].index("r2-appendix")
    t = [c["id"] for c in rest_l].index("c126")                          # the technical section

    def as_long(c):
        x = _src(c)
        for a, b in SHORT_ONLY_TEXT.get(c["id"], ()):
            assert x.count(a) == 1, (c["id"], a)
            x = x.replace(a, b)
        if c["id"] == "rw-data-intro":
            x = x.replace(" Month 7 is used only for results: nothing is learned, chosen or set on it.", "")
        return x
    key_s = lambda c: (c["cell_type"], as_long(c))                       # type and text only: ids, metadata, outputs
    key_l = lambda c: (c["cell_type"], _src(c))
    assert [key_l(c) for c in rest_l[:k] + rest_l[t:]] == [key_s(c) for c in rest_s]   # same cells (type and text), same order
    assert all(_src(c).count("### A.") <= 1 for c in rest_l[k:t])


def test_short_notebook_thick_line_and_nothing_above_it_points_below():
    """Round 5 ([owner-18], [analyst-51]): one thick line, directly after 5.2 and before the technical section, in the short
    notebook only; no link above it points to an anchor below it, and nothing above it mentions the technical section.
    Neither the short nor the final notebook names the long notebook, in any cell, text or output."""
    short, long_ = _cells("savehitl_results.ipynb"), _cells("savehitl_results_long.ipynb")
    ids = [c["id"] for c in short]
    assert [c["id"] for c in short if "<hr" in _src(c)] == ["r5-thick-line"]
    assert not any("<hr" in _src(c) for c in long_)
    i = ids.index("r5-thick-line")
    assert short[i]["cell_type"] == "markdown" and ids[i - 1] == "c125" and _src(short[i + 1]).startswith("# Technical section")
    above = "\n".join(_src(c) for c in short[:i] if c["cell_type"] == "markdown")
    below = "\n".join(_src(c) for c in short[i + 1:] if c["cell_type"] == "markdown")
    anchors_above = set(re.findall(r'<a id="([^"]+)"></a>', above))
    for link in re.findall(r"\]\(#([^)]+)\)", above):
        assert link in anchors_above, link
    assert set(re.findall(r'<a id="([^"]+)"></a>', below)).isdisjoint(re.findall(r"\]\(#([^)]+)\)", above))
    assert "technical section" not in above.lower()                      # the final notebook has no technical section
    for name in ("savehitl_results.ipynb", "savehitl_results_final.ipynb"):
        for c in _cells(name):
            whole = json.dumps(c, ensure_ascii=False).lower()            # source, outputs and metadata
            assert "long notebook" not in whole and "savehitl_results_long" not in whole, (name, c["id"])
    assert ids.index("c141") > i and "nb.hand_back()" in _src(short[ids.index("c141")])   # the archive cell stays below the line


def test_both_notebooks_write_the_same_files():
    from savehitl.views.sections import NOT_SHOWN_IN_SHORT, ITEMS
    short, long_ = _cells("savehitl_results.ipynb"), _cells("savehitl_results_long.ipynb")
    files = [c for c in short if c["id"] == "r2-files"]
    assert len(files) == 1
    written = re.findall(r'"([^"]+)"', _src(files[0]).split("nb.write_files(", 1)[1])
    assert written == NOT_SHOWN_IN_SHORT
    cell_of = lambda items: {c for i in items for c in ITEMS[i]["cells"]}
    # every view cell the long notebook runs is run by the short one too (shown, or written without display), except
    # the months graph, which only the long notebook runs
    assert "F-months" in _items(long_) and "F-months" not in _items(short) + written
    assert cell_of(_items(long_)) - {"F-months"} == cell_of(_items(short) + written)
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

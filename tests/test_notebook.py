"""The notebook's step order and arguments, and the verdict symbols (display only)."""
import os

from savehitl import notebook as nb, runner


def test_need_runs_each_step_once_after_what_it_reads(monkeypatch, tmp_path):
    nb.L = runner.Layout(str(tmp_path))
    nb.TUNE = False
    ran = []
    monkeypatch.setattr(runner, "run_step", lambda L, step, module, args, label=None, quiet=False: ran.append((step, module, args)))
    nb.need("verdicts3")
    names = [s for s, _, _ in ran]
    assert len(names) == len(set(names))
    order = [s for s, _, _ in nb.STEPS]
    assert names == [s for s in order if s in names]                       # chain order
    assert "summaries" not in names and "ranking" not in names               # nothing the section does not read
    for s, _, _ in ran:
        for d in nb._deps(s):
            assert names.index(d) < names.index(s)
    router = dict(zip(*[iter(next(a for s, _, a in ran if s == "router"))] * 2))
    assert router["--tune"] == "false" and router["--train"] == os.path.join(nb.L.outputs, "train_alert")
    b3 = dict(zip(*[iter(next(a for s, _, a in ran if s == "bootstrap3"))] * 2))
    assert b3["--counts-file"] == os.path.join(nb.L.outputs, "bootstrap2", "p2_bootstrap_counts_uint8.npy")


def test_switch_true_passes_tune_true(monkeypatch, tmp_path):
    nb.L = runner.Layout(str(tmp_path))
    nb.TUNE = True
    ran = []
    monkeypatch.setattr(runner, "run_step", lambda L, step, module, args, label=None, quiet=False: ran.append((step, args)))
    nb.need("router")
    assert dict(zip(*[iter(ran[-1][1])] * 2))["--tune"] == "true"


def test_verdict_symbols():
    from savehitl.views import lib as L
    assert L.symbol("beats") == "✅" and L.symbol("does worse") == "❌" and L.symbol("no difference shown") == "🟡"
    assert L.symbol("beats", deciding=True) == "✅*"
    assert L.symbol("does worse (deciding verdict: see P2-T3)") == "❌*"
    assert L.symbol("conditional") == "conditional" and L.symbol(None) is None


def test_hand_back_shows_only_name_and_size(monkeypatch, tmp_path, capsys):
    """The last cell shows the archive's name and size, nothing else (no path, no other text)."""
    nb.L = runner.Layout(str(tmp_path))
    z = tmp_path / "savehitl_returned_outputs.zip"
    z.write_bytes(b"x" * 1234)
    monkeypatch.setattr(runner, "sh", lambda L, cmd, cwd=None, env=None: f"noise\n{z}\n")
    nb.hand_back()
    assert capsys.readouterr().out == "savehitl_returned_outputs.zip: 1,234 bytes\n"


# ---------------------------------------------------------------- the item mapping
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS = os.path.join(ROOT, "savehitl", "views", "cells")
READERS = r"(?:L\.csv|L\.path|L\.desc_load|L\.record|keyed_rows)\("


def _built_items():
    nbk = json.load(open(os.path.join(ROOT, "savehitl_results.ipynb"), encoding="utf-8"))
    items = []
    for c in nbk["cells"]:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        calls = re.findall(r"nb\.section\(([^)]*)\)", src)
        for arg in calls:
            m = re.fullmatch(r'\s*"([^"]+)"\s*', arg)
            assert m, f"nb.section called with something other than one literal item name: {arg!r}"
            items.append(m.group(1))
    return items


def _closure(steps):
    out, todo = set(), list(steps)
    while todo:
        s = todo.pop()
        if s not in out:
            out.add(s)
            todo += nb._deps(s)
    return out


def _reads(item):
    """(step, file) pairs item's views read, found statically in its loading cells and its own cell."""
    from savehitl.views import lib
    from savehitl.views.sections import ITEMS
    spec = ITEMS[item]
    reads = set()
    for name in ["_data_" + d for d in spec["data"]] + spec["cells"]:
        src = open(os.path.join(CELLS, name + ".py"), encoding="utf-8").read()
        for arg in re.findall(READERS + r"\s*([^,)]*)", src):
            m = re.fullmatch(r'\s*["\']([A-Za-z0-9_]+)["\']\s*', arg)
            assert m, f"{name}: a read whose key or step is not a literal ({arg!r}); the static check cannot see it"
        for k in re.findall(r'["\']([A-Za-z0-9_]+)["\']', src):
            if k in lib.KEYS:
                reads.add(lib.KEYS[k])
        for step in re.findall(r'L\.record\(\s*["\']([A-Za-z0-9_]+)["\']\s*\)', src):
            reads.add((step, "record.json"))
    return reads


def _coverage_faults():
    """Static coverage, independent of cell order: (R1) each item's entry lists every step whose output its views read;
    (closure) every file its views read is produced by a step in the closure of its entry."""
    faults = []
    for item, entry in nb.NEEDS.items():
        clo = _closure(entry)
        for step, f in sorted(_reads(item)):
            if step not in entry:
                faults.append((item, step, f, "step not listed in the entry"))
            if step not in clo:
                faults.append((item, step, f, "step not in the closure of the entry"))
    return faults


def test_a_every_built_item_is_in_the_mapping():
    from savehitl.views.sections import ITEMS
    items = _built_items()
    assert len(items) == 38          # rework: P3-T8 no longer shown; F-months, F-data, P3-F11, P3-T10 added
    missing = [i for i in items if i not in nb.NEEDS]
    assert missing == []
    assert set(nb.NEEDS) <= set(ITEMS)                           # no entry for a name the views step does not know
    known = {s for s, _, _ in nb.STEPS}
    assert all(s in known for e in nb.NEEDS.values() for s in e)


def test_b_static_coverage():
    assert _coverage_faults() == []
    # the shared helper cells read only through a parameter (keyed_rows(key, ...)), which the items pass as literals
    for name in ("_defs", "_defs_grid"):
        src = open(os.path.join(CELLS, name + ".py"), encoding="utf-8").read()
        assert set(re.findall(READERS + r"\s*([^,)]*)", src)) <= {"key"}


def test_c_unknown_item_stops_before_any_step(monkeypatch, tmp_path):
    nb.L = runner.Layout(str(tmp_path))
    nb.TUNE = False
    ran = []
    monkeypatch.setattr(runner, "run_step", lambda *a, **k: ran.append(a))
    for name in ("3.1", "no-such-item", "P3-T1R"):
        try:
            nb.section(name)
        except KeyError as e:
            assert repr(name) in str(e)
        else:
            raise AssertionError(f"{name}: no error")
    assert ran == []
    assert not hasattr(nb, "DEFAULT_NEEDS")


def test_d_mutation_ranking_removed_from_P3_T1r_fails_coverage(monkeypatch):
    entry = [s for s in nb.NEEDS["P3-T1r"] if s != "ranking"]
    monkeypatch.setitem(nb.NEEDS, "P3-T1r", entry)
    faults = _coverage_faults()
    assert faults and {f[0] for f in faults} == {"P3-T1r"} and {f[1] for f in faults} == {"ranking"}


def test_d2_mutation_the_r2_242_fault_fails_the_closure_part(monkeypatch):
    """The fault found in an earlier development run: neither ranking nor summaries requested for P3-T1r."""
    monkeypatch.setitem(nb.NEEDS, "P3-T1r", ["policy2", "verdicts2", "policy3", "verdicts3"])
    faults = _coverage_faults()
    assert {(f[1], f[3]) for f in faults} >= {("ranking", "step not in the closure of the entry"),
                                               ("summaries", "step not in the closure of the entry")}

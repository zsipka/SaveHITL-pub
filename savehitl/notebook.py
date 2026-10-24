"""What the notebook's own cells call. Runs in the notebook's Python (Colab's or the examiner's) and uses the standard
library and IPython's display only; every computation runs as a step in the pinned environment (`runner.run_step`).

* `start(hyperparam_tune)`: the layout of this run and the state of the switch.
* `setup(fifar_download_allowed)`: environment, framework and FiFAR, each once per session (`runner`).
* `section(name)`: runs the steps the item `name` needs (NEEDS, by item name; an unknown name stops) that have not run
  yet, in chain order, then the item's views step, and shows what that step wrote (tables, graphs, text) in order.
* `write_files(*names)`: as `section` for each item, but shows nothing (the files of items a notebook does not show).
* `run_time_table()`, `switch_state()`, `input_checksums()`: the technical section's records of this run, read from the
  run's own log.
* `hand_back()`: the folder and archive of the run's outputs to bring back (`returned.build`); on Colab it is offered
  for download.
"""
import html
import json
import os
import sys

from . import runner

L = None
TUNE = None

# step -> (module, arguments as (flag, value) with "@step" for that step's output folder and "@step/file" for a file in
# it). In chain order; `section` runs each step once, after the steps it reads.
STEPS = [
    ("applications", "applications", []),
    ("generator", "generator", []),
    ("draw", "draw", []),
    ("policy1", "policy1", []),
    ("policy1_intervals", "policy1_intervals", [("--policy1", "@policy1")]),
    ("policy2", "policy2", [("--policy1", "@policy1"), ("--generator", "@generator"), ("--draw", "@draw")]),
    ("bootstrap2", "bootstrap2", [("--policy1", "@policy1"), ("--policy1-intervals", "@policy1_intervals"), ("--policy2", "@policy2")]),
    ("verdicts2", "verdicts", [("--policy", "2"), ("--p2u-over", "non-anchor"), ("--policy1", "@policy1"), ("--replay", "@policy2"),
                               ("--boot-record", "@bootstrap2/record.json"), ("--boot-intervals", "@bootstrap2/p2_boot_intervals.csv")]),
    ("train_alert", "train_alert", [("--draw", "@draw")]),
    ("router", "router", [("--train", "@train_alert"), ("--generator", "@generator"), ("--draw", "@draw"), ("--tune", "$TUNE")]),
    ("predict", "predict", [("--policy1", "@policy1"), ("--router", "@router")]),
    ("policy3", "policy3", [("--policy1", "@policy1"), ("--generator", "@generator"), ("--draw", "@draw"), ("--predict", "@predict"),
                            ("--policy2", "@policy2")]),
    ("bootstrap3", "bootstrap3", [("--policy1", "@policy1"), ("--policy3", "@policy3"), ("--counts-record", "@bootstrap2/record.json"),
                                  ("--counts-file", "@bootstrap2/p2_bootstrap_counts_uint8.npy")]),
    ("verdicts3", "verdicts", [("--policy", "3"), ("--p2u-over", "non-anchor"), ("--policy1", "@policy1"), ("--replay", "@policy3"),
                               ("--boot-record", "@bootstrap3/record.json"), ("--boot-intervals", "@bootstrap3/p3_boot_intervals.csv")]),
    ("ranking", "ranking", [("--generator", "@generator"), ("--draw", "@draw"), ("--router", "@router"), ("--predict", "@predict")]),
    ("summaries", "summaries", [("--generator", "@generator"), ("--draw", "@draw"), ("--policy2", "@policy2"), ("--policy3", "@policy3"),
                                ("--ranking", "@ranking")]),
    ("descriptive", "descriptive", [("--policy1", "@policy1"), ("--policy2", "@policy2"), ("--policy3", "@policy3"),
                                    ("--generator", "@generator"), ("--summaries", "@summaries")]),
]
LABELS = {"applications": "the applications: aggregate figures of Base.csv", "generator": "regenerating the 50 reviewers", "draw": "drawing the five teams", "policy1": "policy 1, full automation",
          "policy1_intervals": "policy 1, ranges (1,000 re-draws)", "policy2": "policy 2, naive review (replay)",
          "bootstrap2": "policy 2, re-drawing the cases (50,000)", "verdicts2": "policy 2, verdicts",
          "train_alert": "router's training files", "router": "router's 250 models", "predict": "router's scores on the test month",
          "policy3": "policy 3, analyst-aware deferral (routing and replay)", "bootstrap3": "policy 3, re-drawing the cases (50,000)",
          "verdicts3": "policy 3, verdicts", "ranking": "router's ranking quality", "summaries": "summary tables",
          "descriptive": "descriptive figures: age groups, reviewers and Classifier h on the test month",
          "environment": "environment: Python 3.7.9 and the pinned versions", "framework": "framework: OpenL2D at cfe5fd0 with the patches",
          "fifar": "FiFAR: download and checks"}
# item -> the steps whose outputs the item's views read (its shared loading cells and its own cell, `views/sections.py`);
# `need` adds the steps those read. Every item a notebook cell passes to `section` is a key here; any other name stops
# the run. There is no default.
_P1 = ["policy1_intervals"]                    # loading cell p1
_P2 = ["policy2", "verdicts2"]                 # loading cell p2
_P3 = ["policy3", "verdicts3"]                 # loading cell p3
NEEDS = {
    "F-months": ["applications"],
    "F-data": ["applications"],
    "P2-F10": _P2,
    "P3-F10": _P2 + _P3,
    "P3-F11": _P2 + _P3 + ["applications", "descriptive"],
    "P3-F4": _P2 + _P3,
    "P3-T8": _P2 + _P3,
    "rows-split": _P2 + _P3,
    "P3-T1": _P2 + _P3,
    "P3-T1r": _P2 + _P3 + ["ranking", "summaries"],
    "P2-T1": _P2 + ["summaries", "descriptive"],
    "P1-T2": _P1,
    "P1-F1": _P1,
    "P2-F1": _P2 + _P3,
    "P3-F1": _P2 + _P3,
    "P2-F4": _P2,
    "P2-F2": _P2 + _P3,
    "P3-F2": _P2 + _P3,
    "P2-F3": _P2 + _P3,
    "P3-F3": _P2 + _P3,
    "P3-T10": _P2 + _P3 + ["applications", "descriptive"],
    "P2-T4": _P2 + _P3,
    "P3-T4": _P2 + _P3,
    "P2-F5": _P2 + _P3,
    "P3-T7": _P2 + _P3,
    "P3-T9": ["summaries"],
    "P3-F9": ["policy3"],
    "P2-F7": _P2 + _P3,
    "P3-F6": _P2 + _P3,
    "rows-0035": _P2 + _P3,
    "P2-F6": _P2 + _P3,
    "P3-F5": _P2 + _P3,
    "P2-T5": _P2 + _P3,
    "P3-T5": _P2 + _P3,
    "P2-F8": _P2 + _P3,
    "P3-F7": _P2 + _P3,
    "P2-T4-tables": _P2 + _P3,
    "P3-T4-tables": _P2 + _P3,
    "P2-F5-table": _P2 + _P3,
    "P2-F7-tables": _P2 + _P3,
    "P3-F6-tables": _P2 + _P3,
    "T-labels": [],
    "T-P2-T3": _P2 + _P3,
    "T-P3-T3": _P2 + _P3,
}


def needs_of(name):
    """The steps item `name` needs, from NEEDS only. An item not in NEEDS stops with its name."""
    if name not in NEEDS:
        raise KeyError(f"STOP: notebook item {name!r} has no entry in notebook.NEEDS (no default is used)")
    return list(NEEDS[name])


def start(hyperparam_tune, root=None, python=None):
    """The run's layout. `hyperparam_tune` must be True or False (the switch cell). Records the switch and, when the
    repository is a git clone, its commit, in the run's own log."""
    global L, TUNE
    if hyperparam_tune not in (True, False):
        raise SystemExit("STOP: HYPERPARAM_TUNE must be True or False")
    L = runner.Layout(root or runner.PACKAGE_ROOT, python=python)
    TUNE = hyperparam_tune
    commit = None
    if os.path.isdir(os.path.join(L.root, ".git")):
        import subprocess
        r = subprocess.run(["git", "-C", L.root, "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        commit = r.stdout.strip() if r.returncode == 0 else None
    runner.log(L, f"HYPERPARAM_TUNE = {TUNE}", step="switch", hyperparam_tune=TUNE, repository_commit=commit,
               kernel_python=sys.version.split()[0], platform=sys.platform)
    return L


def _marker(name):
    return os.path.join(L.logs, f"_setup_{name}_done")


def setup(fifar_download_allowed):
    """Environment, framework and FiFAR, each once per session (a repeated call skips what is done)."""
    if fifar_download_allowed is not True:
        raise SystemExit("STOP: permission to download FiFAR not given. Set FIFAR_DOWNLOAD_ALLOWED = True in the settings cell "
                         "and run the cells again from the top.")
    for name, fn in (("environment", lambda: runner.install_environment(L)), ("framework", lambda: runner.fetch_framework(L)),
                     ("fifar", lambda: runner.fetch_fifar(L, fifar_download_allowed))):
        if os.path.exists(_marker(name)):
            print(f"{name}: already set up in this session.")
            continue
        fn()
        os.makedirs(L.logs, exist_ok=True)
        open(_marker(name), "w").close()


def _args(spec):
    out = []
    for flag, val in spec:
        if val == "$TUNE":
            val = "true" if TUNE else "false"
        elif val.startswith("@"):
            step, _, rest = val[1:].partition("/")
            val = os.path.join(L.outputs, step, rest) if rest else os.path.join(L.outputs, step)
        out += [flag, val]
    return out


def _deps(step):
    spec = {s: a for s, _, a in STEPS}[step]
    return [v[1:].partition("/")[0] for _, v in spec if v.startswith("@")]


def need(*steps):
    """Runs the given steps, after every step they read, each once."""
    order, seen = [], set()

    def visit(s):
        if s in seen:
            return
        for d in _deps(s):
            visit(d)
        seen.add(s)
        order.append(s)
    for s in steps:
        visit(s)
    rank = {s: i for i, (s, _, _) in enumerate(STEPS)}
    for s in sorted(order, key=rank.get):
        module, spec = {x: (m, a) for x, m, a in STEPS}[s]
        runner.run_step(L, s, module, _args(spec), label=LABELS[s])


def section(name):
    """Computes what the item needs (NEEDS; an unknown item stops), then shows its tables and graphs in order."""
    steps = needs_of(name)
    from IPython.display import display, HTML, Image, Markdown
    need(*steps)
    step = "views_" + name.replace(".", "_")
    out = runner.run_step(L, step, "views", ["--section", name], label=f"tables and graphs: {name}", quiet=True)
    man = json.load(open(os.path.join(out, "manifest.json"), encoding="utf-8"))
    for it in man["items"]:
        p = os.path.join(out, it["file"])
        if it["kind"] == "table":
            display(HTML(open(p, encoding="utf-8").read()))
        elif it["kind"] == "figure":
            display(Image(filename=p))
        elif it["kind"] == "markdown":
            display(Markdown(open(p, encoding="utf-8").read()))
        else:
            print(open(p, encoding="utf-8").read(), end="")


def write_files(*names):
    """Runs the views steps of the given items, each as `section` would, and shows nothing: their table and graph files
    are written to `tables/` and `figures/`. The short notebook calls it for the items only the long notebook shows."""
    for name in names:
        need(*needs_of(name))
        runner.run_step(L, "views_" + name.replace(".", "_"), "views", ["--section", name], label=f"tables and graphs: {name}", quiet=True)


def _table(header, rows):
    h = "".join(f"<th>{html.escape(str(x))}</th>" for x in header)
    b = "".join("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def run_time_table():
    """Run time and memory of this run: each step's wall-clock time and peak memory in bytes, from the run's own log."""
    from IPython.display import display, HTML
    rows, total, views = [], 0.0, {"n": 0, "seconds": 0.0, "peak": None}
    for r in runner.step_table(L):
        total += float(r["seconds"] or 0)
        if r["step"].startswith("tables and graphs: "):          # the views steps, one row in all
            views["n"] += 1
            views["seconds"] += float(r["seconds"])
            if r["peak_memory_bytes"] is not None:
                views["peak"] = max(views["peak"] or 0, int(r["peak_memory_bytes"]))
            views["platform"] = r["platform"]
            continue
        pm = "—" if r["peak_memory_bytes"] is None else f"{int(r['peak_memory_bytes']):,}"
        rows.append([LABELS.get(r["step"], r["step"]), f"{float(r['seconds']):,.1f}", pm, r["platform"]])
    if views["n"]:
        rows.append([f"tables and graphs ({views['n']} steps; the largest peak)", f"{views['seconds']:,.1f}",
                     "—" if views["peak"] is None else f"{views['peak']:,}", views["platform"]])
    rows.append(["total (steps in this table)", f"{total:,.1f}", "—", sys.platform])
    display(HTML(_table(["step", "wall-clock time (s)", "peak memory (bytes)", "platform"], rows)))


def switch_state():
    print(f"HYPERPARAM_TUNE = {TUNE} in this run: " + ("the router's settings search was run (120 trials per model)." if TUNE else
          "the router's 250 models were refitted from the settings the study's search chose."))


def input_checksums():
    """The input checksum stops of this run and their outcome, from the run's own log and the shipped list."""
    from IPython.display import display, HTML
    rows = runner.input_checksums(L)
    n = {k: sum(1 for r in rows if r["kind"] == k) for k in ("fifar", "framework")}
    done = {}
    p = os.path.join(L.logs, "run_log.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line)
            if r.get("step") in ("framework", "fifar"):
                done[r["step"]] = r["t"]
    out = [["FiFAR files (figshare)", n["fifar"], "each equal to its listed sha256" if "fifar" in done else "not checked in this run"],
           ["framework files (OpenL2D at cfe5fd0, after the patches)", n["framework"],
            "each equal to its listed sha256" if "framework" in done else "not checked in this run"]]
    display(HTML(_table(["inputs", "files listed in results/input_checksums.csv", "outcome"], out)))


def hand_back():
    """Builds the folder and archive of the run's outputs (no alert-level row) and offers the archive for download.
    The cell shows only the archive's name and size; the path and timing go to the run's log only."""
    import time
    t0 = time.time()
    z = runner.sh(L, [L.python, "-B", "-m", "savehitl.returned", L.root], env=dict(os.environ, PYTHONPATH=L.root)).strip().splitlines()[-1]
    size = os.path.getsize(z)
    runner.log(L, f"hand-back archive written ({time.time() - t0:.0f} s).", quiet=True, step="hand_back",
               seconds=round(time.time() - t0, 1), archive=z, archive_bytes=size)
    print(f"{os.path.basename(z)}: {size:,} bytes")
    try:
        from google.colab import files
    except ImportError:
        return
    files.download(z)

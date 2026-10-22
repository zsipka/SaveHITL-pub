"""Step: the tables and graphs of one notebook section (or one item), from the run's own outputs.

Runs the section's cells (savehitl/views/cells/) in one namespace, in the pinned environment, and writes what they
display into this step's folder: HTML tables, PNG graphs, Markdown and text, in order, with `manifest.json`. The notebook
shows them. Table files and graph files named in the text are written to `tables/` and `figures/` at the repository
root. Every input is checked against the checksum its step recorded (assertion log). Texts of the study's views that do
not match a cell of this run are shown as they are and listed in the manifest under `unmapped`, never in the notebook.
"""
import contextlib
import json
import os
import warnings

from . import _common as C

CELLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "views", "cells")


def run_cells(ns, names):
    for n in names:
        p = os.path.join(CELLS, n + ".py")
        exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)


def main():
    a = C.args([("--section", {"required": True})])
    A = C.Asserts(a)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from ..views import lib as L, show as V
    from ..views.sections import SECTIONS, ITEMS
    spec = SECTIONS.get(a.section) or ITEMS.get(a.section)
    A.check(spec is not None, "known notebook section or item", section=a.section)
    L.init(a.L.root, A)
    V.C = V.Collector(a.out)
    plt.show = V.show_plt
    pd.set_option("display.max_rows", 400); pd.set_option("display.max_columns", 60); pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 120)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    ns = {"L": L, "V": V, "np": np, "pd": pd, "plt": plt, "json": json, "os": os, "display": V.display, "Markdown": V.Markdown}
    with contextlib.redirect_stdout(V.C):
        run_cells(ns, ["_defs", "_defs_grid"])
        for d in spec["data"]:
            run_cells(ns, ["_data_" + d])
        for name in spec["cells"]:
            V.C.set_item(name)
            run_cells(ns, [name])
        plt.close("all")
    V.C.close({"section": a.section, "cells": spec["cells"]})
    tables = sorted(os.listdir(L.OUT_TABLES))
    C.write_record(a, {"step": a.step, "section": a.section, "cells": spec["cells"], "shown": len(V.C.items),
                       "unmapped_texts": len(V.C.unmapped), "tables_folder_files": len(tables),
                       "outputs_sha256": C.tree_sha(a.out)})


if __name__ == "__main__":
    main()

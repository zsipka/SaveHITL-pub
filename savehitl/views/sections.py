"""Which tables and graphs each notebook section shows, in order, and which outputs they read.

`data`: the shared loading cells the section needs (p1: policy 1; p2: policy 2's verdicts and cells; p3: policy 3's).
`cells`: the files under `cells/` executed in order, each one table, graph or group of them (the study's item names).
"""
SECTIONS = {
    "data": {"data": [], "cells": ["F-months", "F-data"]},
    "3.1": {"data": ["p2"], "cells": ["P2-F10"]},
    "3.2": {"data": ["p2", "p3"], "cells": ["P3-F10", "P3-F11"]},
    "3.3": {"data": ["p2", "p3"], "cells": ["P3-F4", "P3-T8", "rows-split"]},
    "4.1": {"data": ["p2", "p3"], "cells": ["P3-T1", "P3-T1r"]},
    "5.1": {"data": ["p2"], "cells": ["P2-T1"]},
    "6.1": {"data": ["p1"], "cells": ["P1-T2", "P1-F1"]},
    "6.2a": {"data": ["p2", "p3"], "cells": ["P2-F1", "P3-F1"]},
    "6.2b": {"data": ["p2"], "cells": ["P2-F4"]},
    "6.3": {"data": ["p2", "p3"], "cells": ["P2-F2", "P3-F2"]},
    "6.4": {"data": ["p2", "p3"], "cells": ["P2-F3", "P3-F3", "P3-T10"]},
    "6.5": {"data": ["p2", "p3"], "cells": ["P2-T4", "P3-T4"]},
    "6.6": {"data": ["p2", "p3"], "cells": ["P2-F5", "P3-T7"]},
    "6.7": {"data": [], "cells": ["P3-T9", "P3-F9"]},
    "6.8": {"data": ["p2", "p3"], "cells": ["P2-F7", "P3-F6", "rows-0035"]},
    "7": {"data": ["p2", "p3"], "cells": ["P2-F6", "P3-F5"]},
    "8.3": {"data": ["p2", "p3"], "cells": ["P2-T5", "P3-T5"]},
    "8.4": {"data": ["p2", "p3"], "cells": ["P2-F8", "P3-F7"]},
    "T": {"data": ["p2", "p3"], "cells": ["T-P2-T3", "T-P3-T3"]},
    "T-labels": {"data": [], "cells": ["T-labels"]},
}
# single items, so that a graph can be shown with its own summary below it (entry 9)
ITEMS = {c: {"data": s["data"], "cells": [c]} for s in SECTIONS.values() for c in s["cells"]}
# the item "rows-split" (section 3.3) also writes the table file of P3-T8, which is no longer shown ([analyst-03])
ITEMS["rows-split"] = {"data": ["p2", "p3"], "cells": ["P3-T8", "rows-split"]}
# Items shown in two places (round 2): the graph in the results (both notebooks), the tables in the long notebook's
# appendix. Both parts run the same cell and write the same table files; `PART` selects what is displayed.
for _c, _t in (("P2-T4", "P2-T4-tables"), ("P3-T4", "P3-T4-tables"), ("P2-F5", "P2-F5-table"), ("P2-F7", "P2-F7-tables"),
               ("P3-F6", "P3-F6-tables")):
    ITEMS[_c] = dict(ITEMS[_c], part="graph")
    ITEMS[_t] = dict(ITEMS[_c], part="tables")
# Items the short notebook does not show (the long notebook shows them in its appendix). The short notebook runs their
# views steps without displaying them (`notebook.write_files`), so that both notebooks write the same table and graph files.
NOT_SHOWN_IN_SHORT = ["P1-T2", "P1-F1", "P2-F1", "P2-F4", "P3-F4", "P2-F2", "P3-F2", "P2-F3", "P3-F3", "P3-T7", "P3-T9",
                      "rows-0035", "P2-T5", "P3-T5", "P2-F8", "P3-F7"]

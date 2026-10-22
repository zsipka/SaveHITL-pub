"""Which tables and graphs each notebook section shows, in order, and which outputs they read.

`data`: the shared loading cells the section needs (p1: policy 1; p2: policy 2's verdicts and cells; p3: policy 3's).
`cells`: the files under `cells/` executed in order, each one table, graph or group of them (the study's item names).
"""
SECTIONS = {
    "3.1": {"data": ["p2"], "cells": ["P2-F10"]},
    "3.2": {"data": ["p2", "p3"], "cells": ["P3-F10"]},
    "3.3": {"data": ["p2", "p3"], "cells": ["P3-F4", "P3-T8", "rows-split"]},
    "4.1": {"data": ["p2", "p3"], "cells": ["P3-T1", "P3-T1r"]},
    "5.1": {"data": ["p2"], "cells": ["P2-T1"]},
    "6.1": {"data": ["p1"], "cells": ["P1-T2", "P1-F1"]},
    "6.2a": {"data": ["p2", "p3"], "cells": ["P2-F1", "P3-F1"]},
    "6.2b": {"data": ["p2"], "cells": ["P2-F4"]},
    "6.3": {"data": ["p2", "p3"], "cells": ["P2-F2", "P3-F2"]},
    "6.4": {"data": ["p2", "p3"], "cells": ["P2-F3", "P3-F3"]},
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

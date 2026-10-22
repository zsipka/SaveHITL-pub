"""Step: the draw of the five disjoint teams of ten from the 50 regenerated reviewers.

One call, made once: `numpy.random.RandomState(42).permutation(50)`. Team r (1 to 5) is the reviewers unbiased#i for
i in perm[10(r-1)] .. perm[10r-1]; within a team, the slots are in ascending order of i. Reviewer unbiased#i is paired
with the dataset's reviewer standard#i, whose rows in the training files carry the assignments (FiFAR's
`expert_ids.yaml`, checked by position and name).

Output: teams.json.
"""
import json
import os

import numpy as np
import yaml

from . import _common as C


def main():
    a = C.args()
    A = C.Asserts(a)
    rel = "FiFAR/synthetic_experts/expert_ids.yaml"
    p = os.path.join(a.L.framework, rel)
    A.check(C.sha256(p) == C.input_sha(a.L, rel), "input at its checksum", file=rel)
    human_ids = yaml.safe_load(open(p))["human_ids"]
    A.check(human_ids == [f"standard#{i}" for i in range(50)], "human_ids is standard#0 .. standard#49 in order")
    perm = [int(x) for x in np.random.RandomState(42).permutation(50)]
    teams = {}
    for r in range(1, 6):
        draw_order = perm[10 * (r - 1): 10 * r]
        slot = sorted(draw_order)
        teams[str(r)] = {"name": f"drawn_{r}", "numbers_in_draw_order": draw_order, "numbers_in_slot_order": slot,
                         "twins_in_slot_order": [f"unbiased#{i}" for i in slot],
                         "stored_experts_in_slot_order": [f"standard#{i}" for i in slot]}
    A.check(sorted(sum((t["numbers_in_slot_order"] for t in teams.values()), [])) == list(range(50)),
            "every reviewer in exactly one team")
    rec = {"seed": 42, "call": "numpy.random.RandomState(42).permutation(50)", "generator": "numpy.random.RandomState (MT19937)",
           "numpy_version": np.__version__, "permutation": perm,
           "rule": "drawn team r = unbiased#i for i in perm[10(r-1)] .. perm[10r-1]; slot j = j-th smallest i (as numbers)",
           "teams": teams}
    with open(os.path.join(a.out, "teams.json"), "w") as f:
        json.dump(rec, f, indent=1)
    C.write_record(a, {"step": a.step, "teams_json_sha256": C.sha256(os.path.join(a.out, "teams.json"))})


if __name__ == "__main__":
    main()

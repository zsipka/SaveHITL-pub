"""Step: the router's training files, built by the framework's own script
(`Code/testbed/testbed_train_alert_generation.py`) for the five drawn teams.

Patch 0006 replaces the script's random choice of each team's members by the members of the draw, written into the
script's configuration (`Code/testbed/cfg.yaml`, entries `members` of drawn_1 .. drawn_5); patch 0009 points its
output to this step's folder. This step checks that the members in the patched configuration are those of the draw
step, then runs the script unchanged in its own folder. The script reads FiFAR's alerts and the dataset reviewers'
decisions (months 3 to 7 are read; month 7 is dropped by the script) and writes one `train.parquet` (and its
companion files) per set-up shuffle_<k>#drawn_<r>, 25 set-ups.

Output: <set-up>/... (75 files), as the framework writes them.
"""
import json
import os
import subprocess
import sys

import pandas as pd
import yaml

from . import _common as C

N_FILES = 75


def main():
    a = C.args([("--draw", {"required": True})])
    A = C.Asserts(a)
    L = a.L
    testbed = os.path.join(L.framework, "Code", "testbed")
    for rel in ("Code/testbed/cfg.yaml", "Code/testbed/testbed_train_alert_generation.py",
                "Code/alert_data/dataset_cfg.yaml", "FiFAR/alert_data/processed_data/alerts.parquet",
                "FiFAR/synthetic_experts/expert_predictions.parquet", "FiFAR/synthetic_experts/expert_ids.yaml"):
        A.check(C.sha256(os.path.join(L.framework, rel)) == C.input_sha(L, rel), "input at its checksum", file=rel)
    cfg = yaml.safe_load(open(os.path.join(testbed, "cfg.yaml")))
    draw = json.load(open(os.path.join(a.draw, "teams.json")))
    cap = cfg["environments_train"]["capacity"]
    A.check(sorted(cap) == [f"drawn_{r}" for r in range(1, 6)], "configuration holds drawn_1 .. drawn_5")
    for r in range(1, 6):
        A.check(cap[f"drawn_{r}"]["members"] == draw["teams"][str(r)]["numbers_in_slot_order"],
                "members in the patched configuration equal the draw", team=r)
    dest = os.path.normpath(os.path.join(testbed, cfg["destination_path_train"]))
    A.check(dest == os.path.normpath(a.out), "the script writes into this step's folder", destination=dest)
    r = subprocess.run([sys.executable, "-B", "testbed_train_alert_generation.py"], cwd=testbed,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    with open(os.path.join(a.out, "_script_console.log"), "w") as f:
        f.write(r.stdout)
    A.check(r.returncode == 0, "the framework's script ended without error", exit=r.returncode, tail=r.stdout[-1500:])
    outs = C.tree_sha(a.out)
    outs = {k: v for k, v in outs.items() if k != "record.json"}
    setups = sorted({k.split("/")[0] for k in outs})
    A.check(len(outs) == N_FILES and setups == sorted(f"shuffle_{k}#drawn_{r}" for k in range(1, 6) for r in range(1, 6)),
            "75 files in 25 set-ups", files=len(outs))
    m7 = 0
    for k in outs:
        if k.endswith("train.parquet"):
            m7 += int((pd.read_parquet(os.path.join(a.out, k), columns=["month"])["month"] >= 7).sum())
    A.check(m7 == 0, "no row of month 7 in the training files")
    C.write_record(a, {"step": a.step, "outputs_sha256": outs})


if __name__ == "__main__":
    main()

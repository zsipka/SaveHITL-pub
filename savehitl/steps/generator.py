"""Step: regeneration of the 50 reviewers by the framework's own generator (`Code/synthetic_experts/expert_gen.py`, with
patches 0001 and 0002 applied to the clone).

The framework's configuration (`Code/synthetic_experts/cfg.yaml`) is used with these changes only, each made by
replacing one line and then checked entry by entry against the framework's file:
  * the three paths (dataset configuration, alerts file, output folder);
  * `fitting_set: [3,7]` in place of `[6,7]` (fitted on months 3 to 6);
  * the reviewers' weight on the age attribute `customer_age: [0.0, 0.0]` in place of `[0.07, 0.02]`;
  * the group name `unbiased` (also as `baseline_group`); the order of the feature weights is kept.
The generator runs as `__main__` in the output folder, which holds the configuration it reads.

Outputs (`data/`): expert_parameters.parquet, expert_predictions.parquet, prob_of_error.parquet, expert_ids.yaml;
and targets.csv (each reviewer's target rates and target cost, read from the generator after it ran).
"""
import contextlib
import io
import os
import sys
import time

import yaml

from . import _common as C

OUTPUT_FILES = ("expert_parameters.parquet", "expert_predictions.parquet", "prob_of_error.parquet", "expert_ids.yaml")


def sub_once(A, text, old, new):
    A.check(text.count(old) == 1, "configuration line found exactly once", line=old)
    return text.replace(old, new)


def flatten(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += flatten(v, f"{prefix}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += flatten(v, f"{prefix}[{i}]")
    else:
        out.append((prefix, obj))
    return out


def main():
    a = C.args()
    A = C.Asserts(a)
    L = a.L
    gen_dir = os.path.join(L.framework, "Code", "synthetic_experts")
    gen = os.path.join(gen_dir, "expert_gen.py")
    cfg_path = os.path.join(gen_dir, "cfg.yaml")
    data_cfg = os.path.join(L.framework, "Code", "alert_data", "dataset_cfg.yaml")
    alerts = os.path.join(L.fifar, "alert_data", "processed_data", "alerts.parquet")
    for p in (gen, cfg_path, data_cfg, alerts, os.path.join(gen_dir, "expert_src.py")):
        rel = os.path.relpath(p, L.framework)
        A.check(C.sha256(p) == C.input_sha(L, rel), "input at its checksum", file=rel)
    data_dir = os.path.join(a.out, "data")
    os.makedirs(data_dir)
    text = open(cfg_path).read()
    text = sub_once(A, text, "data_cfg_path: '../alert_data/dataset_cfg.yaml'", f"data_cfg_path: '{data_cfg}'")
    text = sub_once(A, text, "dataset_path: '../../FiFAR/alert_data/processed_data/alerts.parquet'", f"dataset_path: '{alerts}'")
    text = sub_once(A, text, "destination_path: '../../FiFAR/synthetic_experts'", f"destination_path: '{data_dir}'")
    text = sub_once(A, text, "fitting_set: [6,7]", "fitting_set: [3,7]")
    text = sub_once(A, text, "\n    standard:\n", "\n    unbiased:\n")
    text = sub_once(A, text, "        customer_age:\n        - 0.07\n        - 0.02\n", "        customer_age:\n        - 0.0\n        - 0.0\n")
    text = sub_once(A, text, "baseline_group: 'standard'", "baseline_group: 'unbiased'")
    orig, new = yaml.safe_load(open(cfg_path)), yaml.safe_load(text)
    o_flat = flatten(orig)
    n_flat = [(p.replace("/experts/groups/unbiased", "/experts/groups/standard"), v) for p, v in flatten(new)]
    A.check([p for p, _ in o_flat] == [p for p, _ in n_flat], "configuration keys and their order as the framework's")
    allowed = {"/data_cfg_path": data_cfg, "/dataset_path": alerts, "/destination_path": data_dir, "/fitting_set[0]": 3,
               "/experts/groups/standard/w_dict/customer_age[0]": 0.0,
               "/experts/groups/standard/w_dict/customer_age[1]": 0.0, "/baseline_group": "unbiased"}
    changed = [p for (p, ov), (_, nv) in zip(o_flat, n_flat) if ov != nv or type(ov) != type(nv)]
    A.check(all(p in allowed and allowed[p] == dict(n_flat)[p] for p in changed), "only the allowed entries changed",
            changed=changed)
    A.check(list(orig["experts"]["groups"]["standard"]["w_dict"]) == list(new["experts"]["groups"]["unbiased"]["w_dict"]),
            "order of the feature weights kept")
    with open(os.path.join(a.out, "cfg.yaml"), "w") as f:
        f.write(text)
    sys.dont_write_bytecode = True
    sys.path.insert(0, gen_dir)
    cwd = os.getcwd()
    os.chdir(a.out)
    console = io.StringIO()
    t0 = time.time()
    ns = {"__name__": "__main__", "__file__": gen}
    try:
        with contextlib.redirect_stdout(console), contextlib.redirect_stderr(console):
            exec(compile(open(gen).read(), gen, "exec"), ns)
    finally:
        os.chdir(cwd)
    produced = sorted(os.listdir(data_dir))
    A.check(produced == sorted(OUTPUT_FILES), "the generator wrote exactly its four files", files=produced)
    A.check(ns["PROTECTED_COL"] == [{"feature": "customer_age", "protected_class": "higher", "protected_threshold": 50,
                                     "type": "numerical"}], "the generator read the patched protected entry")
    fit_months = sorted(int(m) for m in ns["fit_set"]["month"].unique())
    A.check(set(fit_months) <= {3, 4, 5, 6}, "fitting set within months 3 to 6", months=fit_months)
    # the reviewers' targets, read from the generator's memory after it ran (nothing it computed is changed):
    # target cost per case = lambda (1 - prevalence of the fitting set) x target fpr + prevalence x target miss rate
    lam, prev = float(ns["l"]), float(ns["prevalence"])
    targets = [{"expert": p["expert"], "seed": int(p["seed"]), "alpha_drawn": float(p["alpha"]),
                "target_fpr": float(p["fpr_target"]), "target_fnr": float(p["fnr_target"]),
                "target_cost_per_case": lam * (1 - prev) * float(p["fpr_target"]) + prev * float(p["fnr_target"])}
               for p in ns["expert_properties_list"]]
    A.check(len(targets) == 50, "targets of 50 reviewers")
    import pandas as pd
    pd.DataFrame(targets).to_csv(os.path.join(a.out, "targets.csv"), index=False, float_format="%.17g")
    del ns
    C.write_record(a, {"step": a.step, "generator_seconds": round(time.time() - t0, 2), "configuration_changed": changed,
                       "fit": {"fit_months": fit_months, "prevalence_fit_set": prev, "lambda": lam},
                       "targets_sha256": C.sha256(os.path.join(a.out, "targets.csv")),
                       "outputs_sha256": C.tree_sha(data_dir)})


if __name__ == "__main__":
    main()

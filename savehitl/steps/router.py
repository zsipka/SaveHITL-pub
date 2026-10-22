"""Step: the router's 250 models, one per regenerated reviewer and set-up (25 set-ups of 10), trained by the framework's
own procedure on the training files of step `train_alert`, with the regenerated reviewers' decisions of step
`generator` as targets.

--tune false (default): each model is fitted once with the settings the study's search selected
                        (results/router_selected_settings.csv); see savehitl.router.refit_one.
--tune true:            the framework's full settings search, 120 trials per model (savehitl.router.search_one).

Outputs: models/<set-up>/<reviewer>/best_model.pickle; router_models.csv (per model: sha256, selected trial, weighted
log-loss on month 6, seconds); with --tune true also router_trials.csv (every trial's settings and log-loss).
The models' sha256 are compared with results/router_model_checksums.csv as a record, never a stop.
"""
import json
import os

import pandas as pd
import yaml

from .. import router as RT
from . import _common as C


def main():
    a = C.args([("--train", {"required": True}), ("--generator", {"required": True}), ("--draw", {"required": True}),
                ("--tune", {"required": True, "choices": ["true", "false"]})])
    A = C.Asserts(a)
    L = a.L
    tune = a.tune == "true"
    cfg = yaml.safe_load(open(os.path.join(L.framework, "Code", "alert_data", "dataset_cfg.yaml")))
    twins = pd.read_parquet(os.path.join(a.generator, "data", "expert_predictions.parquet"))
    draw = json.load(open(os.path.join(a.draw, "teams.json")))
    train_rec = json.load(open(os.path.join(a.train, "record.json")))["outputs_sha256"]
    settings = RT.read_settings_table(os.path.join(L.results, "router_selected_settings.csv"))
    shipped = pd.read_csv(os.path.join(L.results, "router_model_checksums.csv"), dtype=str)
    shipped = dict(zip(zip(shipped["setup"], shipped["twin"]), shipped["best_model_sha256"]))
    order = [(r["setup"], r["stored"], r["twin"]) for _, r in settings.iterrows()]
    for setup, stored, twin in order:                 # the table's pairs are those of the draw
        k, t = setup.replace("shuffle_", "").split("#drawn_")
        A.check(stored in draw["teams"][t]["stored_experts_in_slot_order"] and twin == stored.replace("standard#", "unbiased#"),
                "router model pairs a drawn team's slot with its regenerated reviewer", setup=setup, twin=twin)
    A.check(len(order) == 250 and len({(s, w) for s, _, w in order}) == 250, "250 models")
    hpo = RT.load_framework_hpo(L.framework) if tune else None
    if tune:
        A.check(C.sha256(os.path.join(L.framework, "Code/expert_models/hpo.py")) == C.input_sha(L, "Code/expert_models/hpo.py"),
                "input at its checksum", file="Code/expert_models/hpo.py")
    rows, trials, cache = [], [], {}
    for i, (setup, stored, twin) in enumerate(order):
        if setup not in cache:
            cache.clear()
            p = os.path.join(a.train, setup, "train.parquet")
            A.check(C.sha256(p) == train_rec[f"{setup}/train.parquet"], "training file as written by step train_alert", setup=setup)
            ts = pd.read_parquet(p)
            A.check(ts["month"].max() <= 6 and ts.index.name == "case_id", "training file: months up to 6, index case_id", setup=setup)
            cache[setup] = ts
        tx, vx, ty, vy, tw, vw = RT.prepare(cache[setup], stored, twin, twins, cfg)
        mdir = os.path.join(a.out, "models", setup, twin)
        if tune:
            r = RT.search_one(hpo, tx, vx, ty, vy, tw, vw, cfg["data_cols"]["categorical"], mdir)
            for x in r["trials"]:
                trials.append({"setup": setup, "twin": twin, "trial": x["trial"], "params": json.dumps(x["params"], sort_keys=True),
                               "weighted_log_loss": x["weighted_log_loss"], "weighted_log_loss_hex": x["weighted_log_loss_hex"],
                               "seconds": x["seconds"]})
            sel = r["selected_trial"]
        else:
            row = settings.iloc[i]
            r = RT.refit_one(tx, vx, ty, vy, tw, vw, row, os.path.join(mdir, "best_model.pickle"))
            sel = int(row["selected_trial"])
        s = C.sha256(os.path.join(mdir, "best_model.pickle"))
        rows.append({"setup": setup, "stored": stored, "twin": twin, "n_train_rows": len(tx), "n_val_rows": len(vx),
                     "selected_trial": sel, "weighted_log_loss": r["weighted_log_loss"],
                     "weighted_log_loss_hex": r["weighted_log_loss_hex"], "seconds": r["seconds"],
                     "best_model_sha256": s, "equal_to_shipped_checksum": s == shipped.get((setup, twin))})
        print(f"{i + 1}/250 {setup} {twin} {r['seconds']:.1f} s", flush=True)
    m = pd.DataFrame(rows)
    m.to_csv(os.path.join(a.out, "router_models.csv"), index=False, line_terminator="\n")
    if tune:
        pd.DataFrame(trials).to_csv(os.path.join(a.out, "router_trials.csv"), index=False, line_terminator="\n")
    n_eq = int(m["equal_to_shipped_checksum"].sum())
    with open(os.path.join(L.logs, "assertions.jsonl"), "a") as f:     # a record, not a stop
        f.write(json.dumps({"t": C.now(), "step": a.step, "record": "router models equal to the shipped checksums",
                            "equal": n_eq, "of": len(m), "tune": tune}) + "\n")
    C.write_record(a, {"step": a.step, "tune": tune, "models": len(m), "equal_to_shipped_checksums": n_eq,
                       "router_models_csv_sha256": C.sha256(os.path.join(a.out, "router_models.csv"))})


if __name__ == "__main__":
    main()

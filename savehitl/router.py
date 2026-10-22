"""The router of analyst-aware deferral: one model per reviewer, predicting whether that reviewer decides a case
correctly. Trained by OpenL2D's own procedure (`Code/expert_models/run_ova.py` and `hpo.py`).

Two paths, chosen by the notebook's switch `HYPERPARAM_TUNE`:

* `False` (default): each model is fitted once with the settings the study's search selected, read exactly from
  `results/router_selected_settings.csv`. The fit is the one inside the framework's search (`hpo.py`, objective):
  the same constructor with its arguments in the same order, no early stopping, no evaluation set, 10 threads, seed 42,
  then a prediction on the validation month and the weighted log-loss, then the model is pickled.
* `True`: the framework's settings search itself (`hpo.HPO`, 120 trials, TPE sampler with seed 42), imported from the
  framework's code and called unchanged; a thin subclass only records each trial's settings and weighted log-loss.

Data preparation repeats `run_ova.py` lines 28-52 for one reviewer; only the target differs: whether the reviewer's
regenerated decision equals the label.
"""
import contextlib
import io
import json
import math
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

N_JOBS = 10          # run_ova.py:52
INT_SETTINGS = ["max_depth", "n_estimators", "num_leaves", "min_child_samples"]
FLOAT_SETTINGS = ["learning_rate", "reg_alpha", "reg_lambda"]
BOOL_SETTINGS = ["enable_bundle"]
SETTINGS = BOOL_SETTINGS + INT_SETTINGS + FLOAT_SETTINGS


def cat_checker(data, features, cat_dict):
    """run_ova.py:9-15, unchanged."""
    new_data = data.copy()
    for feature in features:
        if new_data[feature].dtype.categories.to_list() != cat_dict[feature]:
            new_data[feature] = pd.Categorical(new_data[feature].values, categories=cat_dict[feature])
    return new_data


def prepare(train_set, expert, twin, twins, cfg):
    """run_ova.py:30-45 for one reviewer slot `expert` of the training file, with the regenerated reviewer `twin`'s
    correctness as the target. Returns train_x, val_x, train_y, val_y, train_w, val_w."""
    train_set = train_set.loc[train_set["assignment"] != "classifier_h"]
    train_exp = train_set.loc[train_set["assignment"] == expert]
    train_exp = cat_checker(train_exp, cfg["data_cols"]["categorical"], cfg["categorical_dict"])
    val_exp = train_exp.loc[train_exp["month"] == 6]
    train_exp = train_exp.loc[train_exp["month"] != 6]
    train_w = train_exp["fraud_bool"].replace([0, 1], [cfg["lambda"], 1])
    val_w = val_exp["fraud_bool"].replace([0, 1], [cfg["lambda"], 1])
    drop = ["fraud_bool", "batch", "month", "assignment", "decision"]
    train_x = train_exp.drop(columns=drop)
    val_x = val_exp.drop(columns=drop)
    train_y = pd.Series((twins.loc[train_exp.index, twin].to_numpy() == train_exp["fraud_bool"].to_numpy()).astype(int),
                        index=train_exp.index)
    val_y = pd.Series((twins.loc[val_exp.index, twin].to_numpy() == val_exp["fraud_bool"].to_numpy()).astype(int),
                      index=val_exp.index)
    return train_x, val_x, train_y, val_y, train_w, val_w


# --- the selected settings table ---------------------------------------------------------------------------------

def settings_to_row(params):
    """One table row from a trial's settings (Python values as the search returned them). Floats are written twice:
    `repr` (shortest exact decimal) and `float.hex` (exact bits)."""
    row = {}
    for k in BOOL_SETTINGS:
        if not isinstance(params[k], bool):
            raise ValueError(f"{k} is not a bool: {params[k]!r}")
        row[k] = "True" if params[k] else "False"
    for k in INT_SETTINGS:
        if isinstance(params[k], bool) or not isinstance(params[k], int):
            raise ValueError(f"{k} is not an int: {params[k]!r}")
        row[k] = str(params[k])
    for k in FLOAT_SETTINGS:
        v = params[k]
        if not isinstance(v, float) or not math.isfinite(v):
            raise ValueError(f"{k} is not a finite float: {v!r}")
        row[k] = repr(v)
        row[k + "_hex"] = v.hex()
    return row


def row_to_settings(row):
    """The settings of one table row, as the Python values the search used. Stops unless the decimal and the hex
    forms of every float give the same bits."""
    s = {}
    for k in BOOL_SETTINGS:
        v = str(row[k])
        if v not in ("True", "False"):
            raise ValueError(f"{k}: {v!r}")
        s[k] = v == "True"
    for k in INT_SETTINGS:
        s[k] = int(str(row[k]))
    for k in FLOAT_SETTINGS:
        a, b = float(str(row[k])), float.fromhex(str(row[k + "_hex"]))
        if a.hex() != b.hex():
            raise ValueError(f"{k}: decimal {row[k]} and hex {row[k + '_hex']} differ")
        s[k] = b
    return s


def read_settings_table(path):
    """The selected settings table, every column read as text (no float parsing by pandas)."""
    t = pd.read_csv(path, dtype=str, keep_default_na=False)
    if t.duplicated(["setup", "twin"]).any():
        raise ValueError("settings table: a (setup, twin) pair appears twice")
    return t


# --- fitting --------------------------------------------------------------------------------------------------------

def fit_from_settings(train_x, train_y, train_w, s, n_jobs=N_JOBS):
    """The framework's fit inside its search objective (hpo.py), with the given settings: same constructor, arguments
    in the same order, no early stopping, no evaluation set."""
    import lightgbm as lgb
    model = lgb.LGBMClassifier(
        importance_type='gain',
        max_depth=s["max_depth"],
        learning_rate=s["learning_rate"],
        n_estimators=s["n_estimators"],
        min_child_samples=s["min_child_samples"],
        num_leaves=s["num_leaves"],
        reg_alpha=s["reg_alpha"],
        reg_lambda=s["reg_lambda"],
        n_jobs=n_jobs,
        boosting_type="dart",
        enable_bundle=s["enable_bundle"],
        seed=42
    )
    model.fit(train_x, train_y, sample_weight=train_w, verbose=False)
    return model


def weighted_log_loss(model, val_x, val_y, val_w):
    """hpo.py's objective value: weighted log-loss of the positive-class probability on the validation month."""
    from sklearn.metrics import log_loss
    y_pred = model.predict_proba(val_x)[:, 1]
    return float(log_loss(y_true=val_y, y_pred=y_pred, sample_weight=val_w))


def save_model(model, path):
    """Pickled as the framework does (hpo.py: `pickle.dump(model, fout)`, default protocol)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fout:
        pickle.dump(model, fout)


def refit_one(train_x, val_x, train_y, val_y, train_w, val_w, settings_row, model_path, n_jobs=N_JOBS):
    """Path HYPERPARAM_TUNE = False for one model. Returns a record: seconds, weighted log-loss (repr and hex)."""
    s = row_to_settings(settings_row)
    t0 = time.perf_counter()
    model = fit_from_settings(train_x, train_y, train_w, s, n_jobs=n_jobs)
    ll = weighted_log_loss(model, val_x, val_y, val_w)
    save_model(model, model_path)
    return {"seconds": round(time.perf_counter() - t0, 4), "weighted_log_loss": repr(ll),
            "weighted_log_loss_hex": ll.hex()}


# --- the full search (HYPERPARAM_TUNE = True) -----------------------------------------------------------------------

def load_framework_hpo(framework_dir):
    """The framework's hpo module, imported from its own code (`Code/expert_models/hpo.py`)."""
    d = os.path.join(framework_dir, "Code", "expert_models")
    if d not in sys.path:
        sys.path.insert(0, d)
    sys.dont_write_bytecode = True
    import hpo  # noqa: E402
    return hpo


def recording_class(hpo):
    class RecordingHPO(hpo.HPO):
        """Stores what the framework's objective returns; changes nothing else."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.search_record = []

        def objective(self, trial):
            t0 = time.perf_counter()
            ll = super().objective(trial)
            self.search_record.append({"trial": trial.number, "params": dict(trial.params),
                                       "weighted_log_loss": repr(float(ll)), "weighted_log_loss_hex": float(ll).hex(),
                                       "seconds": round(time.perf_counter() - t0, 4)})
            return ll
    return RecordingHPO


def search_one(hpo, train_x, val_x, train_y, val_y, train_w, val_w, categorical, model_dir, n_jobs=N_JOBS):
    """Path HYPERPARAM_TUNE = True for one model: the framework's search, as run_ova.py:51-52 calls it. The model kept
    is the framework's own `best_model.pickle` at the selected trial (first of the lowest log-loss)."""
    RecordingHPO = recording_class(hpo)
    os.makedirs(model_dir, exist_ok=True)
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        opt = RecordingHPO(train_x, val_x, train_y, val_y, train_w, val_w, method="TPE", path=model_dir)
        opt.initialize_optimizer(categorical, n_jobs)
    rec = opt.search_record
    if [x["trial"] for x in rec] != list(range(120)):
        raise RuntimeError(f"{model_dir}: the search did not record trials 0 to 119 in order")
    sel = int(np.argmin([float(x["weighted_log_loss"]) for x in rec]))
    with open(os.path.join(model_dir, "search_record.json"), "w") as f:
        json.dump(rec, f, indent=1)
    return {"seconds": round(time.perf_counter() - t0, 4), "selected_trial": sel, "params": rec[sel]["params"],
            "weighted_log_loss": rec[sel]["weighted_log_loss"], "weighted_log_loss_hex": rec[sel]["weighted_log_loss_hex"],
            "trials": rec}

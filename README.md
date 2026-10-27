# SaveHITL-pub

**Purpose:** the code and the executed notebooks that re-run the experiments of the project "Save the human in the loop" on the public FiFAR dataset.

## Contents

| Path | What it is |
|---|---|
| `savehitl_results_final.ipynb` | The notebook, final version: the deciding results first, then the main descriptive results. It is shown executed, with the outputs, tables and graphs of a complete run on Google Colab, so its results can be read without running it. It is `savehitl_results.ipynb` (the short version, also in this repository) without its technical section, which holds the run-time table and the cell that writes the outputs archive; to re-run the whole chain, use `savehitl_results.ipynb` or the long version. |
| `savehitl_results_long.ipynb` | The notebook, long version: the short version plus, in section 2, the graph of which months the study uses and for what, and an appendix of further descriptive results. It is shown executed in the same way. It runs the same computation and writes the same table and graph files, plus that graph's file (`figures/F-months_months_used.png`) |
| `savehitl/` | The one library both notebooks import: what the notebooks' cells call (`notebook.py`), set-up (`runner.py`), memory record (`memory.py`), router refit (`router.py`), the steps of the chain (`steps/`), the bootstrap and verdict code (`boot/`), the tables and graphs (`views/`), and the description of the run's outputs (`returned.py`) |
| `patches/` | Four patch files applied to OpenL2D at commit `cfe5fd0` before the run: `0001` and `0002` (the reviewers' regeneration), `0006` and `0009` (the router's training files for the drawn teams). Each patched file is checked by sha256 before and after |
| `environment.colab.yml` | The pinned environment: Python 3.7.9, NumPy 1.21.6, SciPy 1.7.3, pandas 1.3.5, scikit-learn 0.24.2, LightGBM 3.2.1, pyarrow 12.0.1 |
| `results/router_selected_settings.csv` | The settings the study's search chose for each of the 250 router models; the default run refits the models from them |
| `results/router_model_checksums.csv` | The sha256 of each of the 250 router models of the study |
| `results/input_checksums.csv` | The sha256 of every FiFAR file and of the framework files the run reads; the run stops if any differs |
| `tests/` | Tests of the library (`pytest`) |

## How to run

### Google Colab (the tested route)

Both notebooks are tested on Google Colab. This is the supported way to run them.

1. Open the notebook in Google Colab (File > Open notebook > GitHub, or upload it) and choose a CPU runtime.
2. In the settings cell near the top, `FIFAR_DOWNLOAD_ALLOWED = True` lets the notebook download FiFAR from figshare; with `False` nothing is downloaded and the run stops at the set-up. The executed notebooks show `True`, the value set for the run they display, so running them as they are downloads FiFAR. Set it to `False` if you do not want that. Downloading FiFAR is a use of it under its licence terms (see "Data: FiFAR"). In the switch cell, `HYPERPARAM_TUNE = False` refits the 250 router models from the study's chosen settings; `True` runs the framework's full settings search instead (120 trials per model; more than one free Colab session).
3. Run all cells (Runtime > Run all). If the notebook was opened on its own, the third code cell, after the settings and switch cells, clones this repository into the session. The next cell installs the pinned environment, fetches OpenL2D at commit `cfe5fd0` with its archive `l2d_benchmarking.zip` and applies the patches, and downloads FiFAR; every file is checked by sha256. On Colab this cell takes about 4 minutes. Each results section then runs the steps of the chain it needs, in order, and shows its tables and graphs. Table files go to `tables/` and graph files to `figures/`. Run each notebook in its own fresh runtime: steps already done in the same runtime are not run again.
4. The notebook's table "Run time and memory of this run", at the end of its technical section, gives each step's time and memory figure, measured during the run. Where several steps show exactly the same memory figure, that figure is the lowest the measurement records on Colab, not the step's own peak; for those steps the run does not show their own peak. The table's total covers the listed steps only, not the cloning and zip cells.
5. The last cell writes `savehitl_returned_outputs.zip` and, on Colab, offers it for download, so that the run's outputs can be kept after the session ends. It holds the run's 28 table files (`tables/`); for each step of the chain, its record (`record.json`) and, for most steps, its summary output files, among them the verdicts, the bootstrap intervals and the list of the 250 refitted router models with their checksums; for each table-and-graph step, its record and manifest (`record.json`, `manifest.json`); the per-column summaries of the run's case-level files (`per_column_summaries.csv`: for columns of numbers, count, sum, sum of absolute values, minimum and maximum; for other columns, count, number of distinct values and a checksum of the values); and the run's logs, including its time and memory records (`logs/`). The minimum and maximum of a column are values of single applications, so for FiFAR's columns they are FiFAR data: the zip is for your own use, and if you pass it on, FiFAR's licence terms apply (see "Data: FiFAR"). It holds no graph file and no case row of FiFAR. The archives of the two notebooks differ only in their table-and-graph folders: 37 for the short notebook, 43 for the long one, whose six extra folders belong to the months graph and the appendix tables.

On a free Google Colab CPU runtime, each notebook took about 20 minutes from the set-up cell to the end of its last section; the steps' own times, in the table of step 4, add up to the same. The cloning cell (the third code cell) and the last cell (the zip) add a little to this. The largest step, regenerating the reviewers, peaked at about 5.8 GB of memory. This is the largest step's own peak, not the whole session's: the notebook itself runs alongside it.

### Local machine (documented, not tested)

This route is described for reference only. It has not been tested.

The set-up cell installs micromamba for Linux on x86_64, so the route below assumes such a machine with `git` and Python 3 available.

1. Clone this repository and start Jupyter from its root folder with any Python 3.
2. Run the notebook as on Colab. The set-up cell installs micromamba and the pinned environment into `.tools/` inside the repository; OpenL2D and FiFAR are placed under `openl2d/`; run outputs go to `outputs/` and `logs/`, table and graph files to `tables/` and `figures/`. None of these folders is committed (`.gitignore`).
3. About 5 GB of free disk space is advisable. On the study's own machine, the installed environment, OpenL2D, FiFAR and the run's outputs took about 1.9 GB; the set-up also needs space for the package cache and the downloads, which was not measured. For memory, 16 GB is advisable: the largest step peaked at about 5.8 GB on Colab and at about 4.3 GB on the study's own machine, which has 16 GB, and the notebook itself runs alongside it.

On other systems, the pinned versions may not be available as packages; the notebook stops if any installed version differs from the pinned one.

## What the notebook does not re-run

- **FiFAR itself.** The chain starts from FiFAR's alerts file (`alerts.parquet`): the alert model and the selection of the 30,622 alerts are taken as published.
- **Classifier h.** The framework's shipped model in `l2d_benchmarking.zip` is used as it is; it is not retrained.
- **The router's settings search**, unless `HYPERPARAM_TUNE = True`. By default the 250 router models are refitted from the settings the study's search chose (`results/router_selected_settings.csv`); on the study's machine, a refit from the same settings gave byte-identical models. The run writes their sha256.
- **The study's internal validation checks.** The run asserts its own consistency step by step and stops on a failed assertion; it does not compare its figures with the study's.

Everything else is computed during the run: the regenerated reviewers, the draw of the teams, the router's training files and models, the three policies, the bootstrap intervals, the verdicts and the summary tables.

## Data: FiFAR

- **Dataset:** Financial Fraud Alert Review Dataset (FiFAR), version 1, by
  Jean V. Alves, Diogo Leitão, Sérgio Jesus, Marco O. P. Sampaio, Javier
  Liébana, Pedro Saleiro, Mário A. T. Figueiredo and Pedro Bizarro, 2025.
- **Where it comes from:** figshare,
  https://doi.org/10.6084/m9.figshare.28351172 (version 1).
- **Licence:** CC BY 4.0 (Creative Commons Attribution 4.0 International),
  https://creativecommons.org/licenses/by/4.0/.
- **Article:** Alves et al., *Scientific Data*, 2025. "A benchmarking
  framework and dataset for learning to defer in human-AI decision-making",
  volume 12, article number 506, https://doi.org/10.1038/s41597-025-04664-y.
- **How it is used:** the notebook downloads FiFAR from figshare and uses it
  unmodified. This repository does not hold or pass on any FiFAR file or
  case row. The notebook's saved outputs include aggregate statistics of FiFAR's
  `Base.csv` (rates, counts and correlations); they include no case row or
  individual value.
- **Source of `Base.csv`:** the Bank Account Fraud dataset (Kaggle,
  `sgpjesus/bank-account-fraud-dataset-neurips-2022`), which Kaggle states is
  under CC BY-NC-SA 4.0 (Creative Commons Attribution-NonCommercial-ShareAlike
  4.0 International), https://creativecommons.org/licenses/by-nc-sa/4.0/.
  Kaggle asks users to cite: Jesus et al., "Turning the Tables: Biased,
  Imbalanced, Dynamic Tabular Datasets for ML Evaluation", Neural Information
  Processing Systems conference, 2022. The FiFAR deposit on figshare states
  CC BY 4.0. Users who reuse FiFAR's `Base.csv` should check both licences.
  This project used FiFAR for non-commercial academic work only.
- **Disclaimer:** the figshare deposit states no disclaimer or terms of its
  own. FiFAR is provided under CC BY 4.0, whose Section 5 disclaims
  warranties and limits the licensor's liability. FiFAR's creators have not
  reviewed or endorsed this repository.

### Files in `results/`: derived from FiFAR

This project made the three files in `results/` from its runs on FiFAR
(https://doi.org/10.6084/m9.figshare.28351172, CC BY 4.0,
https://creativecommons.org/licenses/by/4.0/). They are derived from FiFAR,
not part of it.

- `router_selected_settings.csv`: the settings chosen for each of the 250
  router models, with the weighted log-loss of the selected trial
  (column `selected_weighted_log_loss`), which this project computed on
  FiFAR.
- `router_model_checksums.csv`: the checksums of the 250 router models this
  project trained on FiFAR.
- `input_checksums.csv`: the paths, sizes and checksums of the input files,
  132 from FiFAR and 10 from OpenL2D (Apache License 2.0, see `NOTICE`).

They hold no FiFAR case row and no data value from FiFAR: no feature, label,
score, reviewer decision or reviewer parameter. To show what each row refers
to, they reuse FiFAR's own reviewer labels (for example `standard#13`) and
FiFAR's file paths and file sizes. FiFAR's creators have not reviewed or
endorsed these files.

## Code: OpenL2D

OpenL2D's attribution and licence, and the changes this project makes to
its files, are in "Licence" below and in `NOTICE`.

## Licence

This repository, including the files in `results/`, is licensed under the
Apache License, Version 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
The full text is in `LICENSE`. The copyright line and the attributions are
in `NOTICE`.

This work builds on OpenL2D by Feedzai, under the Apache License 2.0. Its
code is not included here. The patch files in `patches/` change four of its
files; `NOTICE` lists each change and its reason.

The datasets are not included in this repository and are not covered by its
licence. FiFAR is under CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). Its `Base.csv` comes from the
Bank Account Fraud dataset, which Kaggle states is under CC BY-NC-SA 4.0
(https://creativecommons.org/licenses/by-nc-sa/4.0/). See "Data: FiFAR".

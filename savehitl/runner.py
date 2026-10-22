"""Set-up and step runner used by the notebook. Runs in the notebook's own Python and uses the standard library only.

* `install_environment`: micromamba and Python 3.7.9 with the pinned versions (`environment.colab.yml`).
* `fetch_framework`: OpenL2D at commit cfe5fd0 from GitHub, its archive `l2d_benchmarking.zip` (which holds the shipped
  Classifier h) through Git Large File Storage, and the patch files in `patches/`; every file stopped on sha256.
* `fetch_fifar`: FiFAR from figshare, stopped on figshare's size and MD5, then every file on its sha256.
* `run_step`: one step of the chain, as a child process of the pinned Python; its wall time and peak memory (converted by
  platform) go into the run's log, from which `step_table` builds the table of run time and memory.

Every stop raises `SystemExit` with a plain message. The run's own log (`logs/`) is not part of the notebook.
"""
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

from . import memory

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GITHUB = "https://github.com/feedzai/openl2d.git"
UPSTREAM = "cfe5fd00850684a321187e41bdd49719a96a0ba1"
UPSTREAM_TREE = "1c180e779d7f237e6c1cc699c33b620190638a80"
LFS_ARCHIVE = ("l2d_benchmarking.zip", "5eb113485ecde0a1aa5699a81f05483ad9fdc7d91672a7c3c23d5fa0ca61b873", 60388435)
FIFAR_URL = "https://ndownloader.figshare.com/files/52147616"
FIFAR_SIZE = 209350760
FIFAR_MD5 = "2255e7b8a391d0ab567f37ec27e52f3d"
MICROMAMBA_URL = "https://github.com/mamba-org/micromamba-releases/releases/download/2.9.0-0/micromamba-linux-64"
MICROMAMBA_SHA = "366cd9cd8be14df1ab8ed50352a82111082a36686b2d389fdb79a92c3fafb3e3"
PINNED_VERSIONS = {"python": "3.7.9", "numpy": "1.21.6", "scipy": "1.7.3", "pandas": "1.3.5", "scikit-learn": "0.24.2",
                   "lightgbm": "3.2.1", "pyarrow": "12.0.1"}
# (patch file, file it changes, sha256 before, sha256 after); applied in this order to the clone at cfe5fd0
PATCHES = [
    ("0001-expert_gen-w_dict-protected-weights.patch", "Code/synthetic_experts/expert_gen.py",
     "139d8e78bf228e2bb599f1e568207672f1447bab78b941f5009d8cc66fd18a23", "95c57dcfa3613f047f21fbffb5ed8ebf923170568afdc8b89e69d44883df2bac"),
    ("0002-dataset_cfg-protected-entry-customer_age.patch", "Code/alert_data/dataset_cfg.yaml",
     "7c831577f39f6dd5f7196a1af3cdf162978fbdd3d5806b28e5d463a84c8a4825", "48422f8a07800146b77a7592a481e6dcbea1a6aa8088ebcc0726bd380d045221"),
    ("0006-testbed-drawn-teams-membership.patch", "Code/testbed/testbed_train_alert_generation.py",
     "3d21f24f0e32f14b2adb7499bcfce2834376cb8a6790b43aae6586390bda9015", "18222d355f1ae0f9f03c5d3813cf6b4d482f2dbbc0ff712f8df014ca7a69271d"),
    ("0006-testbed-drawn-teams-membership.patch", "Code/testbed/cfg.yaml", None, None),   # second hunk; checked after 0009
    ("0009-testbed_cfg-destination_path_train-drawn-teams-relative.patch", "Code/testbed/cfg.yaml",
     "06b9d4839c7a3880694a39ec671a56683c87d3d58b393dba453031b7fb2e2b72", "0d37d2223ed9f559ef448d20ac97a3d6f072a80d273c1d51b099900df9e5ca97"),
]


class Layout:
    """Where everything lives. `root` is the folder of this repository."""

    def __init__(self, root=PACKAGE_ROOT, python=None):
        self.root = os.path.abspath(root)
        self.framework = os.path.join(self.root, "openl2d")
        self.fifar = os.path.join(self.framework, "FiFAR")
        self.outputs = os.path.join(self.root, "outputs")
        self.logs = os.path.join(self.root, "logs")
        self.tools = os.path.join(self.root, ".tools")
        self.mamba = os.path.join(self.tools, "micromamba")
        self.mamba_root = os.path.join(self.tools, "mamba")
        self.env = os.path.join(self.mamba_root, "envs", "savehitl")
        self.python = python or os.path.join(self.env, "bin", "python")
        self.results = os.path.join(self.root, "results")
        self.patches = os.path.join(self.root, "patches")


# --- small helpers -------------------------------------------------------------------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def stop(L, msg):
    log(L, "STOP: " + msg)
    raise SystemExit("STOP: " + msg)


def log(L, msg, quiet=False, **kw):
    """Appends one record to the run's own log (logs/run_log.jsonl) and prints the message (unless `quiet`)."""
    os.makedirs(L.logs, exist_ok=True)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "msg": msg, **kw}
    with open(os.path.join(L.logs, "run_log.jsonl"), "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    if not quiet:
        print(msg, flush=True)


def sh(L, cmd, cwd=None, env=None):
    r = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0:
        stop(L, f"command failed ({r.returncode}): {' '.join(cmd)}\n{r.stdout[-1500:]}\n{r.stderr[-3000:]}")
    return r.stdout


def download(url, dest, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def input_checksums(L):
    """results/input_checksums.csv: kind, path (relative to the framework clone), size, sha256."""
    with open(os.path.join(L.results, "input_checksums.csv")) as f:
        return list(csv.DictReader(f))


# --- set-up --------------------------------------------------------------------------------------------------------

def install_environment(L):
    """micromamba, then Python 3.7.9, then LightGBM and the numerical pins, then ortools, then the pinned pip set."""
    t0 = time.time()
    os.makedirs(L.tools, exist_ok=True)
    if not os.path.exists(L.mamba):
        download(MICROMAMBA_URL, L.mamba)
    if sha256(L.mamba) != MICROMAMBA_SHA:
        stop(L, "micromamba binary differs from its published sha256")
    os.chmod(L.mamba, 0o755)
    yml = open(os.path.join(L.root, "environment.colab.yml")).read()
    conda = re.findall(r"^  - ([A-Za-z0-9_.\-]+=[^\s]+)\s*$", yml, re.M)
    pins = re.findall(r"^      - ([A-Za-z0-9_.\-]+==[^\s]+)\s*$", yml, re.M)
    python = [c for c in conda if c.startswith("python=")]
    rest = [c for c in conda if not c.startswith("python=")]
    env = dict(os.environ, MAMBA_ROOT_PREFIX=L.mamba_root)
    base = ["-r", L.mamba_root, "-y", "--override-channels", "-c", "conda-forge"]
    if not os.path.exists(L.python):
        sh(L, [L.mamba, "create", "-n", "savehitl", *base, *python], env=env)
        sh(L, [L.mamba, "install", "-n", "savehitl", *base, *rest], env=env)
        sh(L, [L.python, "-m", "pip", "install", "ortools==9.5.2237"])
        pinfile = os.path.join(L.tools, "pip_pins.txt")
        with open(pinfile, "w") as f:
            f.write("\n".join(pins) + "\n")
        sh(L, [L.python, "-m", "pip", "install", "-r", pinfile])
    check_environment(L, pins)
    log(L, f"Environment ready ({time.time() - t0:.0f} s).", step="environment", seconds=round(time.time() - t0, 1))


def check_environment(L, pins=()):
    freeze = sh(L, [L.python, "-m", "pip", "freeze"])
    norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
    got = {norm(l.split("==")[0]): l.split("==")[1] for l in freeze.splitlines() if "==" in l}
    wrong = {p.split("==")[0]: got.get(norm(p.split("==")[0])) for p in pins if got.get(norm(p.split("==")[0])) != p.split("==")[1]}
    out = sh(L, [L.python, "-c", "import sys, numpy, scipy, pandas, sklearn, lightgbm, pyarrow; print(sys.version.split()[0], "
                 "numpy.__version__, scipy.__version__, pandas.__version__, sklearn.__version__, lightgbm.__version__, "
                 "pyarrow.__version__)"]).split()
    versions = dict(zip(PINNED_VERSIONS, out))
    log(L, "environment versions", versions=versions, pip_freeze_sha256=hashlib.sha256(freeze.encode()).hexdigest(),
        pip_pins_not_as_pinned=wrong)
    if versions != PINNED_VERSIONS:
        stop(L, f"library versions {versions} differ from the pinned {PINNED_VERSIONS}")
    if wrong:
        stop(L, f"pip pins not installed as pinned: {wrong}")


def fetch_framework(L):
    """OpenL2D at cfe5fd0, l2d_benchmarking.zip extracted at its root, patches applied; each step stopped on sha256."""
    t0 = time.time()
    if os.path.exists(L.framework) and os.listdir(L.framework):
        stop(L, f"{L.framework} exists and is not empty; start from a fresh copy of the repository")
    os.makedirs(L.framework, exist_ok=True)
    g = lambda *a: sh(L, ["git", "-C", L.framework, *a])
    g("init", "-q")
    g("remote", "add", "origin", GITHUB)
    g("fetch", "-q", "--depth", "1", "origin", UPSTREAM)
    if g("rev-parse", "FETCH_HEAD").strip() != UPSTREAM or g("rev-parse", UPSTREAM + "^{tree}").strip() != UPSTREAM_TREE:
        stop(L, "the fetched framework commit or its tree is not the pinned one")
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
    sh(L, ["git", "-C", L.framework, "-c", "filter.lfs.smudge=", "-c", "filter.lfs.process=", "-c", "filter.lfs.required=false",
           "checkout", "-q", UPSTREAM], env=env)
    name, oid, size = LFS_ARCHIVE
    pointer = open(os.path.join(L.framework, name)).read()
    if f"oid sha256:{oid}" not in pointer or f"size {size}" not in pointer:
        stop(L, f"{name}: the pointer in cfe5fd0 differs from the recorded object")
    body = json.dumps({"operation": "download", "transfers": ["basic"], "objects": [{"oid": oid, "size": size}]}).encode()
    req = urllib.request.Request(GITHUB + "/info/lfs/objects/batch", data=body, method="POST",
                                 headers={"Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json"})
    o = json.load(urllib.request.urlopen(req, timeout=60))["objects"][0]
    if "error" in o:
        stop(L, f"{name}: Git Large File Storage refused the download: {o['error']}")
    dest = os.path.join(L.tools, name)
    os.makedirs(L.tools, exist_ok=True)
    download(o["actions"]["download"]["href"], dest, o["actions"]["download"].get("header"))
    if os.path.getsize(dest) != size or sha256(dest) != oid:
        stop(L, f"{name}: the downloaded archive differs from its object id")
    with zipfile.ZipFile(dest) as z:
        z.extractall(L.framework)
    apply_patches(L)
    bad = [r["path"] for r in input_checksums(L) if r["kind"] == "framework"
           and sha256(os.path.join(L.framework, r["path"])) != r["sha256"]]
    if bad:
        stop(L, f"framework files differ from the input checksum list: {bad}")
    log(L, f"Framework ready at {UPSTREAM[:7]} with the patches ({time.time() - t0:.0f} s).", step="framework",
        seconds=round(time.time() - t0, 1))


def apply_patches(L):
    files = []
    for pf, target, before, _ in PATCHES:
        if pf not in files:
            files.append(pf)
        if before is not None and sha256(os.path.join(L.framework, target)) != before:
            stop(L, f"{target} differs from the framework's file at {UPSTREAM[:7]}")
    for pf in files:
        sh(L, ["git", "-C", L.framework, "apply", "--whitespace=nowarn", os.path.join(L.patches, pf)])
    for pf, target, _, after in PATCHES:
        if after is not None and sha256(os.path.join(L.framework, target)) != after:
            stop(L, f"patch {pf}: {target} differs from the expected patched file")


def fetch_fifar(L, allowed):
    """FiFAR from figshare (CC BY 4.0), checked against figshare's size and MD5, then file by file."""
    if allowed is not True:
        stop(L, "the FiFAR download is not allowed: set FIFAR_DOWNLOAD_ALLOWED = True to proceed")
    t0 = time.time()
    dest = os.path.join(L.tools, "FiFAR.zip")
    os.makedirs(L.tools, exist_ok=True)
    if not os.path.exists(dest):
        download(FIFAR_URL, dest)
    md5 = hashlib.md5(open(dest, "rb").read()).hexdigest()
    if os.path.getsize(dest) != FIFAR_SIZE or md5 != FIFAR_MD5:
        stop(L, f"FiFAR.zip differs from figshare's published size and MD5 ({os.path.getsize(dest)}, {md5})")
    with zipfile.ZipFile(dest) as z:
        z.extractall(L.framework)                       # the archive holds FiFAR/ at its top
    rows = [r for r in input_checksums(L) if r["kind"] == "fifar"]
    bad = [r["path"] for r in rows if not os.path.isfile(os.path.join(L.framework, r["path"]))
           or sha256(os.path.join(L.framework, r["path"])) != r["sha256"]]
    have = {os.path.relpath(os.path.join(d, f), L.framework) for d, _, fs in os.walk(L.fifar) for f in fs}
    extra = sorted(have - {r["path"] for r in rows})
    if bad or extra:
        stop(L, f"FiFAR files differ from the input checksum list: differing {bad[:5]}, extra {extra[:5]}")
    os.remove(dest)
    log(L, f"FiFAR ready: {len(rows)} files, each equal to its checksum ({time.time() - t0:.0f} s).", step="fifar",
        seconds=round(time.time() - t0, 1))


# --- steps ---------------------------------------------------------------------------------------------------------

def run_step(L, step, module, args=(), label=None, quiet=False):
    """Runs `python -m savehitl.steps.<module> --out <outputs/step> ...` in the pinned Python. Records wall time and peak
    memory (bytes, converted by platform) in the run's log. Stops if the step fails."""
    out = os.path.join(L.outputs, step)
    if os.path.exists(os.path.join(out, "_done.json")):
        log(L, f"{step}: already done in this session; not run again.", quiet=quiet)
        return out
    os.makedirs(out, exist_ok=True)
    os.makedirs(L.logs, exist_ok=True)
    cmd = [L.python, "-B", "-m", f"savehitl.steps.{module}", "--layout-root", L.root, "--out", out, *[str(a) for a in args]]
    env = dict(os.environ, PYTHONPATH=L.root, PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    with open(os.path.join(L.logs, f"{step}_stdout.txt"), "w") as so, open(os.path.join(L.logs, f"{step}_stderr.txt"), "w") as se:
        p = subprocess.Popen(cmd, cwd=L.root, env=env, stdout=so, stderr=se)
        _, status, ru = os.wait4(p.pid, 0)
    wall = time.time() - t0
    rc = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
    peak = memory.convert(ru.ru_maxrss)
    rec = {"step": step, "label": label or step, "exit": rc, "seconds": round(wall, 2), "peak_memory": peak}
    with open(os.path.join(L.logs, "steps.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    if rc != 0:
        tail = open(os.path.join(L.logs, f"{step}_stderr.txt")).read()[-2500:]
        stop(L, f"{step} exited {rc}. Last lines of its error output:\n{tail}")
    with open(os.path.join(out, "_done.json"), "w") as f:
        json.dump(rec, f)
    log(L, f"{label or step}: done in {wall:.0f} s.", quiet=quiet, **rec)
    return out


def step_table(L):
    """The table of run time and peak memory of every step of this run, from the run's own log (rows in run order).
    Returns a list of dicts: step, seconds, peak memory in bytes, platform."""
    rows = []
    for name in ("run_log.jsonl", "steps.jsonl"):
        p = os.path.join(L.logs, name)
        if not os.path.exists(p):
            continue
        for line in open(p):
            r = json.loads(line)
            if name == "run_log.jsonl" and r.get("step") in ("environment", "framework", "fifar"):
                rows.append({"order": r["t"], "step": r["step"], "seconds": r["seconds"], "peak_memory_bytes": None,
                             "platform": sys.platform})
            elif name == "steps.jsonl":
                pm = r["peak_memory"]
                rows.append({"order": None, "step": r["label"], "seconds": r["seconds"], "peak_memory_bytes": pm["bytes"],
                             "platform": pm["platform"]})
    return rows

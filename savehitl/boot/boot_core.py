"""
Shared core of the policy 2 and policy 3 bootstraps. Plan step 2.1 (Implement and run the sweep; run register).
Designs: policy 2 design version 0.4, section 7 (adopted by policy 3 design version 0.13, section 7), frozen at
Gate 1. Build routes: M1 to M4, X1 to X6, L1 to L5; M5, G-a to G-c, F, L5 limit;
M6, T-a to T-d; F without purgeable pages, information-only bounds, owner-present display.

Library copy of the study's bootstrap core: the computing functions are unchanged; only the memory functions of the
study's machine are left out. Every function takes its sizes as arguments. The real scripts assert the design's values (N = 4,457, B = 50,000, seed 2026).

What lives here, and nothing else:
  - the index matrix from the exact call, in one call, its sha256, check G1;
  - the per-resample counts, built row block by row block from the index matrix, guards G-a and G-b;
  - the counts file (route M6 producer): write, sha256 of file and of array bytes, read-back check;
  - the M6 consumer checks T-a to T-d;
  - (in the study's own scripts, not here: the launch conditions measured on the study's machine; in this library the
    memory watchdog is `savehitl.memory.Watchdog`);
  - the sums engine: counts block (uint8) converted to float64, times integer-valued per-case vectors (M1, M2);
  - percentile intervals, NumPy's default linear method (G2), on the defined resamples only.
Decisions are coded 1 = alert confirmed, 0 = alert dismissed.
"""
import hashlib
import os

import numpy as np

from .. import memory

EXACT_CALL = "numpy.random.RandomState(2026).randint(0, 4457, size=(50000, 4457))"
G1_CALL = "numpy.random.RandomState(2026).randint(0, 4457, size=(1000, 4457))"
GENERATOR = "numpy.random.RandomState (MT19937)"
ZERO = 1e-9                      # zero threshold (policy 2 design section 7)
L4_FACTOR = 1.84                 # the P2-G (e) factor
L5_CAP_BYTES = 8_000_000_000     # the lower of 0.75 x F and 8 GB (decimal)


# ---------------------------------------------------------------------------------------------- checksums
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(a, rows_per_chunk=2000):
    """sha256 of the raw array bytes in C order, hashed in row chunks (no full copy). The array must be
    C-contiguous; a memory-mapped array is read chunk by chunk."""
    assert a.flags["C_CONTIGUOUS"], "array must be C-contiguous"
    h = hashlib.sha256()
    if a.ndim == 1:
        h.update(memoryview(np.ascontiguousarray(a)).cast("B"))
        return h.hexdigest()
    for r0 in range(0, a.shape[0], rows_per_chunk):
        h.update(memoryview(np.ascontiguousarray(a[r0:r0 + rows_per_chunk])).cast("B"))
    return h.hexdigest()


def case_order_sha(case_ids):
    """sha256 of the ordered case_id vector, as little-endian int64 bytes."""
    v = np.asarray(case_ids)
    assert v.ndim == 1 and np.all(np.diff(v) > 0), "case ids must be strictly ascending"
    return hashlib.sha256(v.astype("<i8").tobytes()).hexdigest()


def peak_rss():
    """Peak resident memory of this process in bytes, converted by platform; raw value if not known."""
    rec = memory.peak()
    return rec["bytes"] if rec["bytes"] is not None else rec["raw"]


# ---------------------------------------------------------------------------------------------- index and counts
def draw_index(seed, n, b):
    """The exact call, in one call, with the default 64-bit integer type (no dtype argument)."""
    idx = np.random.RandomState(seed).randint(0, n, size=(b, n))
    assert idx.dtype == np.int64 and idx.shape == (b, n) and idx.flags["C_CONTIGUOUS"]
    return idx


def check_g1(idx, seed, n, rows=1000):
    """G1: the first `rows` rows equal a fresh RandomState(seed).randint(0, n, size=(rows, n))."""
    fresh = np.random.RandomState(seed).randint(0, n, size=(rows, n))
    ok = bool(np.array_equal(idx[:rows], fresh))
    n_diff = int((idx[:rows] != fresh).sum())
    del fresh
    return ok, n_diff


def counts_from_index(idx, n, block_rows=2000, guard_max=255):
    """Per-resample counts: counts[r, j] = number of times case j is drawn in resample r.
    Built block by block from the int64 index (offsets + bincount, in int64). Guards, tested before the cast:
      G-a: every count is at most `guard_max` (255 for uint8);
      G-b: every row sums to n, in a 64-bit sum.
    Returns (counts uint8 (b, n) C order, record). A failed guard raises GuardError (the run stops)."""
    b = idx.shape[0]
    out = np.empty((b, n), dtype=np.uint8)
    max_count = 0
    bad_rows = 0
    for r0 in range(0, b, block_rows):
        blk = idx[r0:r0 + block_rows]
        m = blk.shape[0]
        off = blk + (np.arange(m, dtype=np.int64)[:, None] * n)
        c = np.bincount(off.ravel(), minlength=m * n).reshape(m, n)         # int64
        del off
        mx = int(c.max())
        max_count = max(max_count, mx)
        if mx > guard_max:
            raise GuardError("G-a", f"count {mx} above {guard_max} in rows {r0} to {r0 + m - 1}")
        rs = c.sum(axis=1, dtype=np.int64)
        nb = int((rs != n).sum())
        bad_rows += nb
        if nb:
            raise GuardError("G-b", f"{nb} rows of rows {r0} to {r0 + m - 1} do not sum to {n}")
        out[r0:r0 + m] = c.astype(np.uint8)                                  # cast after both guards
        del c
    return out, {"G-a_max_count": max_count, "G-a_limit": guard_max, "G-a": "pass",
                 "G-b_rows_not_summing": bad_rows, "G-b": "pass", "block_rows": block_rows,
                 "storage": "uint8, C order, row r = resample r, column j = j-th case in ascending case_id"}


class GuardError(Exception):
    def __init__(self, guard, msg):
        super().__init__(f"{guard} failed: {msg}")
        self.guard = guard


def row_sums_ok(counts, n, block_rows=2000):
    """G-b on any counts array (also T-c): every row sums to n, in a 64-bit sum. Returns (ok, n_bad_rows)."""
    bad = 0
    for r0 in range(0, counts.shape[0], block_rows):
        bad += int((counts[r0:r0 + block_rows].sum(axis=1, dtype=np.int64) != n).sum())
    return bad == 0, bad


def counts_of_rows(idx_rows, n):
    """Counts for a few index rows (T-d), int64."""
    m = idx_rows.shape[0]
    off = idx_rows + (np.arange(m, dtype=np.int64)[:, None] * n)
    return np.bincount(off.ravel(), minlength=m * n).reshape(m, n)


# ---------------------------------------------------------------------------------------------- counts file (M6)
def save_counts(counts, path):
    """Write the counts as .npy (lossless, uncompressed), exclusively; then read back memory-mapped and compare
    the sha256 of the array bytes. Returns the record."""
    assert counts.dtype == np.uint8 and counts.flags["C_CONTIGUOUS"]
    if os.path.exists(path):
        raise FileExistsError(path)
    arr_sha = sha256_array(counts)
    with open(path, "xb") as f:
        np.save(f, counts, allow_pickle=False)
    file_sha = sha256_file(path)
    back = np.load(path, mmap_mode="r", allow_pickle=False)
    back_ok = (back.shape == counts.shape and back.dtype == counts.dtype and back.flags["C_CONTIGUOUS"]
               and sha256_array(back) == arr_sha)
    rec = {"path": path, "shape": list(counts.shape), "dtype": str(counts.dtype), "byte_order": counts.dtype.byteorder,
           "byte_order_note": "'|' = not applicable (one-byte type)", "order": "C", "format": "NumPy .npy, uncompressed",
           "file_size_bytes": os.path.getsize(path), "file_sha256": file_sha, "array_bytes_sha256": arr_sha,
           "read_back_array_bytes_sha256_equal": bool(back_ok)}
    del back
    return rec


def m6_checks(path, rec, case_ids, seed, n, b, g1_rows=1000, numpy_version_recorded=None):
    """Route M6 consumer checks, in order, before any comparison. Each returns pass/fail with
    its figures. `rec` is the producer's record (file sha256, array-bytes sha256, shape, dtype, case-order sha256).
    Returns (results, counts) where counts is the loaded array (in memory) or None if T-a fails."""
    res = {}
    # T-a: file checksum, then array-bytes checksum, shape and dtype after loading
    fsha = sha256_file(path)
    ta_file = fsha == rec["file_sha256"]
    counts = None
    ta_arr = ta_shape = False
    if ta_file:
        counts = np.load(path, allow_pickle=False)
        ta_shape = (list(counts.shape) == [b, n] == list(rec["shape"]) and str(counts.dtype) == "uint8" == rec["dtype"]
                    and counts.flags["C_CONTIGUOUS"])
        ta_arr = ta_shape and sha256_array(counts) == rec["array_bytes_sha256"]
    res["T-a"] = {"result": "pass" if (ta_file and ta_arr and ta_shape) else "fail", "file_sha256": fsha,
                  "file_sha256_equal": ta_file, "array_bytes_sha256_equal": bool(ta_arr), "shape_dtype_ok": bool(ta_shape)}
    if res["T-a"]["result"] != "pass":
        return res, None
    # T-b: case order
    cs = case_order_sha(case_ids)
    res["T-b"] = {"result": "pass" if cs == rec["case_order_sha256"] else "fail", "case_order_sha256": cs}
    # T-c: G-b on reload
    ok, nbad = row_sums_ok(counts, n)
    res["T-c"] = {"result": "pass" if ok else "fail", "rows_not_summing": nbad}
    # T-d: a fresh draw of rows 0 to g1_rows-1, turned into counts, equals the file's rows
    fresh = np.random.RandomState(seed).randint(0, n, size=(g1_rows, n))
    fc = counts_of_rows(fresh, n)
    del fresh
    eq = bool(np.array_equal(fc, counts[:g1_rows].astype(np.int64)))
    res["T-d"] = {"result": "pass" if eq else "fail", "rows_compared": g1_rows,
                  "cells_differing": int((fc != counts[:g1_rows]).sum())}
    del fc
    if numpy_version_recorded is not None:
        res["numpy_version"] = {"result": "pass" if np.__version__ == numpy_version_recorded else "fail",
                                "this_run": np.__version__, "policy_2_run": numpy_version_recorded}
    return res, counts


# ---------------------------------------------------------------------------------------------- sums engine
def resample_sums(counts, V, block_rows=2000, with_point=False):
    """S = counts @ V, for all rows: counts (b, n) uint8 is converted to float64 one row block at a time (M2; G-c:
    no arithmetic in 8 bits); V (n, m) holds integer-valued float64. Every product and partial sum is an integer
    below 2^53, so the result is exact whatever the block shape.
    with_point=True: row 0 is the full sample (every case once) and rows 1 to b the resamples."""
    assert V.dtype == np.float64 and V.shape[0] == counts.shape[1]
    assert np.all(V == np.round(V)) and np.abs(V).max(initial=0) * counts.shape[1] * 255 < 2 ** 53
    b = counts.shape[0]
    o = 1 if with_point else 0
    S = np.empty((b + o, V.shape[1]), dtype=np.float64)
    if with_point:
        S[0] = V.sum(axis=0)
    for r0 in range(0, b, block_rows):
        Wf = counts[r0:r0 + block_rows].astype(np.float64)
        S[o + r0:o + r0 + Wf.shape[0]] = Wf @ V
        del Wf
    return S


def full_sample_sums(V):
    """The point estimate: every case once (weights 1)."""
    return V.sum(axis=0, keepdims=True)


# ---------------------------------------------------------------------------------------------- intervals
def adjusted_percentiles(n_deciding):
    """Interval ends of the deciding intervals, at full precision: 2.5/n % and 100 - 2.5/n %."""
    lo = 2.5 / n_deciding
    return lo, 100.0 - lo


def interval(x, ok, q_lo, q_hi):
    """Percentile interval on the defined resamples (G2: NumPy's default linear interpolation)."""
    v = x[ok]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    lo, hi = np.percentile(v, [q_lo, q_hi])
    return float(lo), float(hi), int(v.size)


def verdict_word(lo, hi):
    """Policy 2 design section 7: lower end above 0 'does worse'; upper end below 0 'beats'; otherwise
    'no difference shown'. Ends within 1e-9 of 0 count as 0."""
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "not defined"
    lo0 = 0.0 if abs(lo) <= ZERO else lo
    hi0 = 0.0 if abs(hi) <= ZERO else hi
    if lo0 > 0:
        return "does worse"
    if hi0 < 0:
        return "beats"
    return "no difference shown"

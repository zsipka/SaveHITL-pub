"""Display layer of the notebook's tables and graphs, run in the pinned environment by the step `views`.

Ported from the study's results-notebook display helpers. Display only: nothing here reads a step output, computes a
figure or changes a value. Every displayed object is written in order into the section's view folder by the collector
(`outputs/views_<section>/`): tables as HTML, graphs as PNG, text as Markdown or plain text, with a `manifest.json` that
lists them in order. The notebook shows them in that order.

`show(df, key, ...)` displays a copy of a frame with columns hidden, labels renamed and cell texts mapped one to one.
A cell text that has no mapping, or a named cell that does not hold the expected text, is shown as it is and listed in
the manifest under `unmapped` (texts that follow from the run's results may differ from the study's); it is never shown
in the notebook. `txt`, `say` and `md` fill a text template.
"""
import io
import json
import os
import sys

DASH = "—"


class Collector:
    def __init__(self, out):
        self.out = out
        os.makedirs(out, exist_ok=True)
        self.items = []
        self.unmapped = []
        self._buf = io.StringIO()
        self._item = None

    def set_item(self, name):
        self.flush_text()
        self._item = name

    def _add(self, kind, ext, payload, binary=False, **meta):
        self.flush_text()
        n = len(self.items) + 1
        name = f"{n:03d}_{kind}.{ext}"
        with open(os.path.join(self.out, name), "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
            f.write(payload)
        self.items.append({"n": n, "kind": kind, "file": name, "item": self._item, **meta})

    def write(self, s):              # print() lands here
        self._buf.write(s)

    def flush(self):
        pass

    def flush_text(self):
        s = self._buf.getvalue()
        if s.strip():
            self._buf = io.StringIO()
            self._add("text", "txt", s)
        else:
            self._buf = io.StringIO()

    def markdown(self, s):
        self._add("markdown", "md", s)

    def table(self, df, key):
        self._add("table", "html", df._repr_html_(), key=key, rows=int(df.shape[0]), columns=int(df.shape[1]))

    def figure(self, fig):
        from . import lib
        lib.retext_figure(fig)
        b = io.BytesIO()
        fig.savefig(b, format="png", dpi=90, bbox_inches="tight")
        self._add("figure", "png", b.getvalue(), binary=True)

    def note_unmapped(self, **kw):
        self.unmapped.append(dict(kw, item=self._item))

    def close(self, extra=None):
        self.flush_text()
        with open(os.path.join(self.out, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(dict({"items": self.items, "unmapped": self.unmapped}, **(extra or {})), f, indent=1, ensure_ascii=False)


C = None      # the section's collector, set by the step


def display(obj):
    import pandas as pd
    if isinstance(obj, pd.DataFrame):
        C.table(obj, getattr(obj, "attrs", {}).get("savehitl_view"))
    elif isinstance(obj, pd.Series):
        C.table(obj.to_frame(), None)
    elif isinstance(obj, Markdown):
        C.markdown(obj.data)
    else:
        print(obj)


class Markdown:
    def __init__(self, data):
        self.data = data


def show_plt():
    import matplotlib.pyplot as plt
    for num in plt.get_fignums():
        C.figure(plt.figure(num))
    plt.close("all")


def _fill(key, template, fmap, fields):
    shown = dict(fields)
    for name, m in (fmap or {}).items():
        if name in shown:
            k = str(shown[name])
            if k in m:
                shown[name] = m[k]
            else:
                C.note_unmapped(where="text", key=key, field=name, value=k)
    return template.format(**shown)


def txt(key, template, fmap=None, **fields):
    from . import lib
    return lib.display_text(_fill(key, template, fmap, fields))


def say(key, template, fmap=None, **fields):
    print(txt(key, template, fmap, **fields))


def md(key, template, fmap=None, **fields):
    C.markdown(txt(key, template, fmap, **fields))


def _missing(x):
    import pandas as pd
    if x is None or x is pd.NA or x is pd.NaT:
        return True
    try:
        return isinstance(x, float) and x != x or (hasattr(x, "dtype") and getattr(x, "ndim", 1) == 0 and bool(pd.isna(x)))
    except (TypeError, ValueError):
        return False


def _empty_cells(v):
    """A copy of `v` with every missing value or None shown as DASH (as in the study's notebook)."""
    import pandas as pd
    from pandas.io.formats.format import format_array
    miss = [[_missing(x) for x in v.iloc[:, j].tolist()] for j in range(v.shape[1])]
    if not any(any(m) for m in miss):
        return v
    data = {}
    for j in range(v.shape[1]):
        s = v.iloc[:, j]
        if not any(miss[j]):
            data[j] = s.reset_index(drop=True)
        elif s.dtype.kind == "f":
            data[j] = pd.Series([t.strip() for t in format_array(s._values, None, na_rep=DASH)], dtype=object)
        else:
            data[j] = pd.Series([DASH if m else x for x, m in zip(s.tolist(), miss[j])], dtype=object)
    out = pd.DataFrame(data)
    out.index = v.index
    out.columns = v.columns
    return out


def _display_terms(v):
    """The notebook's display terminology (lib.DISPLAY_TERMS) on a display copy: column and index labels, and text cells."""
    from . import lib
    import pandas as pd
    t = lib.display_text

    def lab(x):
        return tuple(t(y) for y in x) if isinstance(x, tuple) else t(x)
    v = v.copy()
    v.columns = pd.MultiIndex.from_tuples([lab(c) for c in v.columns], names=[t(n) for n in v.columns.names]) \
        if isinstance(v.columns, pd.MultiIndex) else pd.Index([lab(c) for c in v.columns], name=t(v.columns.name))
    v.index = pd.MultiIndex.from_tuples([lab(c) for c in v.index], names=[t(n) for n in v.index.names]) \
        if isinstance(v.index, pd.MultiIndex) else pd.Index([lab(c) for c in v.index], name=t(v.index.name))
    for j in range(v.shape[1]):
        if v.iloc[:, j].dtype == object:
            v.iloc[:, j] = [t(x) for x in v.iloc[:, j].tolist()]
    return v


def show(df, key, hide=(), rename=None, index_names=None, column_names=None, values=None, index=None, cells=None, empty_cells=False):
    """Display copy of `df` (see the module text). Columns to hide must exist; value maps and named cells are applied
    where they match and recorded where they do not."""
    v = df.copy()
    if hide:
        missing = [c for c in hide if c not in v.columns]
        assert not missing, f"view {key}: columns to hide not found: {missing}"
        v = v.drop(columns=list(hide))
    for col, m in (values or {}).items():
        assert col in v.columns, f"view {key}: column for a value map not found: {col}"
        col_cells = v[col].astype(object).where(v[col].notna(), None)
        unknown = sorted({str(c) for c in col_cells if c is not None and str(c).strip() not in m})
        for u in unknown:
            C.note_unmapped(where="view", key=key, column=str(col), value=u)
        v[col] = [None if c is None else m.get(str(c).strip(), c) for c in col_cells]
    for row, col, old, new in (cells or []):
        ri = [i for i, r in enumerate(v.index) if str(r) == row]
        ci = [j for j, c in enumerate(v.columns) if str(c) == col]
        if len(ri) == 1 and len(ci) == 1 and v.iat[ri[0], ci[0]] is not None and str(v.iat[ri[0], ci[0]]) == old:
            v.iat[ri[0], ci[0]] = new
        else:
            C.note_unmapped(where="cell", key=key, row=row, column=col, expected=old)
    if index:
        v = v.rename(index=lambda x: index.get(str(x), x))
    if rename:
        v = v.rename(columns=lambda x: rename.get(str(x), x))
    if index_names:
        v.index = v.index.set_names([index_names.get(n, n) for n in v.index.names])
    if column_names:
        v.columns = v.columns.set_names([column_names.get(n, n) for n in v.columns.names])
    if empty_cells:
        v = _empty_cells(v)
    v = _display_terms(v)
    v.attrs["savehitl_view"] = key
    display(v)

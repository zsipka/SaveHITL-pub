# Technical section: the label texts word for word, as set in savehitl/views/lib.py; the table files carry them in their
# `label` columns.
USED = [("L_P1", "P1-T2"), ("L_P2_DEC", "P2-T3"), ("L_P2K", "P2-T3"), ("L_P3_DEC", "P3-T3"),
        ("L_DESC", "P2-T4, P2-T5, P2-F5, P2-F7, P3-T4, P3-T5, P3-F6, P3-T7"), ("L_RULE", "P2-T3c, P3-T3c"), ("L_T8", "P3-T8"),
        ("L_AA", "P3-T9"), ("T9_C_ZERO", "P3-T9"), ("T9_B_EQUAL", "P3-T9"), ("T9_P2_C_CELL", "P3-T9"), ("T9_ROW_I_NOTE", "P3-T9"),
        ("T9_NOT_DEFINED", "P3-T9"), ("F9_C_ZERO", "P3-F9"), ("F9_P2_C", "P3-F9"), ("F9_B_EQUAL", "P3-F9"), ("F9_NOTE", "P3-F9")]
V.md('T-labels', "\n\n".join(f"**{k}**, used by: {u}\n\n```text\n{getattr(L, k)}\n```" for k, u in USED), {})

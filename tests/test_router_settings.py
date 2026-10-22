"""Build tests: the shipped settings table reads back to exact values."""
import os

from savehitl import router as RT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_table_reads_back_exactly():
    t = RT.read_settings_table(os.path.join(ROOT, "results", "router_selected_settings.csv"))
    assert len(t) == 250
    for _, r in t.iterrows():
        s = RT.row_to_settings(r)
        assert RT.row_to_settings(RT.settings_to_row(s)) == s
        for k in RT.FLOAT_SETTINGS:
            assert s[k].hex() == r[k + "_hex"]

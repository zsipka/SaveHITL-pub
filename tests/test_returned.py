"""The per-column summaries of the returned folder: count, sum, sum of absolute values, minimum, maximum."""
import pandas as pd

from savehitl import returned


def test_numeric_and_text_columns():
    df = pd.DataFrame({"x": [1.5, -2.0, None], "t": ["a", "b", "a"]}, index=pd.Index([7, 8, 9], name="case_id"))
    rows = {r["column"]: r for r in returned.summarise_frame(df, "f.parquet")}
    assert set(rows) == {"case_id", "x", "t"}
    x = rows["x"]
    assert x["count"] == 2 and float(x["sum"]) == -0.5 and float(x["sum_abs"]) == 3.5
    assert float(x["min"]) == -2.0 and float(x["max"]) == 1.5
    assert rows["t"]["n_distinct"] == 2 and len(rows["t"]["values_sha256"]) == 64
    assert float(rows["case_id"]["sum"]) == 24.0


def test_alert_level_rule(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("case_id,v\n1,2\n")
    q = tmp_path / "b.csv"
    q.write_text("team,v\nA,2\n")
    assert returned.is_alert_level(str(p), "policy2") and not returned.is_alert_level(str(q), "policy2")
    assert returned.is_alert_level(str(q), "train_alert")

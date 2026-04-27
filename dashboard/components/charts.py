from __future__ import annotations

import pandas as pd
import plotly.express as px


def f1_line(df: pd.DataFrame):
    if df.empty:
        return px.line(title="F1 over time")
    return px.line(df, x="created_at", y="overall_f1", color="model_name", title="F1 over time")


def slice_bar(df: pd.DataFrame):
    if df.empty:
        return px.bar(title="Slice F1")
    return px.bar(df, x="slice", y="f1", color="slice", title="Slice F1")
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def f1_line(df: pd.DataFrame):
    if df.empty:
        return px.line(title="F1 over time")
    return px.line(df, x="created_at", y="overall_f1", color="model_name", title="F1 over time")


def slice_bar(df: pd.DataFrame):
    if df.empty:
        return px.bar(title="Slice F1")
    chart = px.bar(
        df,
        x="slice",
        y="candidate_f1",
        color="status",
        title="Slice comparison",
        color_discrete_map={
            "improved": "#16a34a",
            "within_tolerance": "#6b7280",
            "baseline": "#2563eb",
            "regressed": "#dc2626",
            "missing": "#9ca3af",
        },
    )
    chart.update_traces(texttemplate="%{y:.3f}", textposition="outside")
    chart.update_layout(xaxis_title="Slice", yaxis_title="Candidate F1")
    return chart


def metric_delta_heatmap(df: pd.DataFrame):
    if df.empty:
        return go.Figure()

    heatmap = go.Figure(
        data=go.Heatmap(
            z=[df["delta"].tolist()],
            x=df["metric"].tolist(),
            y=["Δ candidate vs champion"],
            colorscale=[
                [0.0, "#b91c1c"],
                [0.5, "#9ca3af"],
                [1.0, "#15803d"],
            ],
            zmid=0,
            text=[[f"{value:.3f}" for value in df["delta"].tolist()]],
            texttemplate="%{text}",
            hovertemplate="Metric=%{x}<br>Delta=%{z:.3f}<extra></extra>",
        )
    )
    heatmap.update_layout(title="Metric delta heatmap", margin=dict(l=0, r=0, t=40, b=0))
    return heatmap


def slice_delta_heatmap(df: pd.DataFrame):
    if df.empty:
        return go.Figure()

    values = [0.0 if value is None else float(value) for value in df["delta"].tolist()]
    heatmap = go.Figure(
        data=go.Heatmap(
            z=[values],
            x=df["slice"].tolist(),
            y=["Δ slice F1"],
            colorscale=[
                [0.0, "#b91c1c"],
                [0.5, "#9ca3af"],
                [1.0, "#15803d"],
            ],
            zmid=0,
            text=[["—" if value is None else f"{float(value):.3f}" for value in df["delta"].tolist()]],
            texttemplate="%{text}",
            hovertemplate="Slice=%{x}<br>Delta=%{z:.3f}<extra></extra>",
        )
    )
    heatmap.update_layout(title="Slice delta heatmap", margin=dict(l=0, r=0, t=40, b=0))
    return heatmap


def kl_trend_line(df: pd.DataFrame):
    if df.empty:
        return px.line(title="KL divergence trend")
    chart = px.line(
        df.sort_values("created_at"),
        x="created_at",
        y="kl_divergence",
        color="feature",
        markers=True,
        title="KL divergence trend",
    )
    chart.update_layout(yaxis_title="KL divergence", xaxis_title="Created at")
    return chart
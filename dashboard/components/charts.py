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


def comparison_bar_chart(candidate_metrics: pd.DataFrame, champion_metrics: pd.DataFrame):
    """Side-by-side bar chart comparing candidate vs champion metrics."""
    if candidate_metrics.empty and champion_metrics.empty:
        return px.bar(title="Metric comparison")
    rows = []
    for _, row in candidate_metrics.iterrows():
        metric = row.get("metric", "")
        rows.append({"metric": metric, "value": row.get("candidate", 0.0), "run": "Candidate"})
    for _, row in champion_metrics.iterrows():
        metric = row.get("metric", "")
        rows.append({"metric": metric, "value": row.get("champion", 0.0), "run": "Champion"})
    df = pd.DataFrame(rows)
    if df.empty:
        return px.bar(title="Metric comparison")
    chart = px.bar(
        df,
        x="metric",
        y="value",
        color="run",
        barmode="group",
        title="Candidate vs Champion",
        color_discrete_map={"Candidate": "#2563eb", "Champion": "#6b7280"},
    )
    chart.update_layout(xaxis_title="Metric", yaxis_title="Value")
    return chart


def delta_bar_chart(metrics_df: pd.DataFrame):
    """Bar chart showing deltas with color-coded improvement/regression."""
    if metrics_df.empty:
        return px.bar(title="Metric deltas")
    chart = px.bar(
        metrics_df,
        x="metric",
        y="delta",
        title="Metric Deltas (Candidate − Champion)",
        color="delta",
        color_continuous_scale=[(0, "#dc2626"), (0.5, "#9ca3af"), (1, "#16a34a")],
        range_color=[-max(abs(metrics_df["delta"].min()), abs(metrics_df["delta"].max())),
                      max(abs(metrics_df["delta"].min()), abs(metrics_df["delta"].max()))],
    )
    chart.add_hline(y=0, line_dash="dash", line_color="#6b7280")
    chart.update_layout(xaxis_title="Metric", yaxis_title="Delta")
    return chart


def radar_comparison_chart(candidate_metrics: pd.DataFrame, champion_metrics: pd.DataFrame):
    """Radar (spider) chart for multi-metric comparison."""
    if candidate_metrics.empty and champion_metrics.empty:
        return go.Figure()
    metrics = candidate_metrics["metric"].tolist() if not candidate_metrics.empty else champion_metrics["metric"].tolist()
    if not metrics:
        return go.Figure()
    candidate_vals = []
    champion_vals = []
    for m in metrics:
        c_row = candidate_metrics[candidate_metrics["metric"] == m]
        ch_row = champion_metrics[champion_metrics["metric"] == m]
        candidate_vals.append(float(c_row["candidate"].iloc[0]) if not c_row.empty else 0.0)
        champion_vals.append(float(ch_row["champion"].iloc[0]) if not ch_row.empty else 0.0)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=candidate_vals + [candidate_vals[0]],
        theta=metrics + [metrics[0]],
        fill="toself",
        name="Candidate",
        line_color="#2563eb",
    ))
    fig.add_trace(go.Scatterpolar(
        r=champion_vals + [champion_vals[0]],
        theta=metrics + [metrics[0]],
        fill="toself",
        name="Champion",
        line_color="#6b7280",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        title="Multi-metric radar comparison",
    )
    return fig
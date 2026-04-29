from __future__ import annotations

# ruff: noqa: E402
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.api_client import api_v1_path, safe_api_call
from dashboard.components.charts import (
    comparison_bar_chart,
    delta_bar_chart,
    radar_comparison_chart,
    slice_delta_heatmap,
)
from dashboard.components.connection_status import ensure_api_connection
from dashboard.components.real_time_metrics import (
    auto_refresh_sidebar_controls,
    maybe_auto_refresh,
    refresh_button,
)


def _metric_dataframe(payload: dict) -> pd.DataFrame:
    metric_table = payload.get("metric_table", {}) or {}
    rows = []
    for metric, values in metric_table.items():
        rows.append(
            {
                "metric": metric,
                "champion": values.get("champion", 0.0),
                "candidate": values.get("candidate", 0.0),
                "delta": values.get("delta", 0.0),
                "status": values.get("status", "baseline"),
            }
        )
    return pd.DataFrame(rows)


def _slice_dataframe(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(payload.get("slice_comparison", []) or [])


def _delta_status_label(delta: float) -> str:
    if delta > 0:
        return "🟢 Improved"
    if delta < 0:
        return "🔴 Regressed"
    return "⚪ No change"


def _recommendation(candidate_payload: dict, metrics_df: pd.DataFrame) -> str:
    """Generate a promote/don't-promote recommendation based on gate result and deltas."""
    if candidate_payload.get("passed"):
        regressed = metrics_df[metrics_df["delta"] < 0]
        if regressed.empty:
            return "✅ **Recommendation: PROMOTE** — All metrics improved or held steady."
        max_reg = regressed["delta"].abs().max()
        if max_reg <= 0.02:
            return "✅ **Recommendation: PROMOTE** — Minor regressions within tolerance."
        return "⚠️ **Recommendation: PROMOTE WITH CAUTION** — Passed gate but some regressions exceed 0.02."
    return "❌ **Recommendation: DO NOT PROMOTE** — Gate check failed."


auto_refresh_sidebar_controls()

if ensure_api_connection():
    st.title("Model Comparison")
    refresh_button()

    evals_payload, evals_error = safe_api_call(
        lambda client: client.get(api_v1_path("/evaluations/"))
    )
    if evals_error:
        st.error(evals_error)
    else:
        evals = evals_payload or []
        if not evals:
            st.info("No evaluations available for comparison. Run your first evaluation to get started.")
        else:
            df = pd.DataFrame(evals)
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
            df["label"] = df.apply(
                lambda row: f"{'🏆 ' if row.get('is_current_champion') else ''}{row.get('model_name', '')} v{row.get('model_version', '')} — {'PASS' if row.get('passed') else 'FAIL'} ({row.get('id', '')[:8]})",
                axis=1,
            )

            with st.sidebar:
                st.subheader("Select runs")
                candidate_idx = st.selectbox(
                    "Candidate run",
                    options=range(len(df)),
                    format_func=lambda i: df.iloc[i]["label"],
                    index=0,
                )
                champion_idx = st.selectbox(
                    "Champion run",
                    options=range(len(df)),
                    format_func=lambda i: df.iloc[i]["label"],
                    index=next(
                        (i for i, row in df.iterrows() if row.get("is_current_champion")),
                        0,
                    ),
                )

            candidate_row = df.iloc[candidate_idx]
            champion_row = df.iloc[champion_idx]
            candidate_id = candidate_row.get("id", "")
            champion_id = champion_row.get("id", "")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Candidate")
                st.metric("Model", f"{candidate_row.get('model_name', '')} v{candidate_row.get('model_version', '')}")
                st.metric("F1", f"{candidate_row.get('overall_f1', 0.0):.3f}")
                st.metric("Accuracy", f"{candidate_row.get('overall_accuracy', 0.0):.3f}")
                st.metric("Gate", "✅ PASS" if candidate_row.get("passed") else "❌ FAIL")
            with col2:
                st.subheader("Champion")
                st.metric("Model", f"{champion_row.get('model_name', '')} v{champion_row.get('model_version', '')}")
                st.metric("F1", f"{champion_row.get('overall_f1', 0.0):.3f}")
                st.metric("Accuracy", f"{champion_row.get('overall_accuracy', 0.0):.3f}")
                st.metric("Gate", "✅ PASS" if champion_row.get("passed") else "❌ FAIL")

            # Fetch detailed payloads
            candidate_payload, cand_err = safe_api_call(
                lambda client: client.get(api_v1_path(f"/evaluations/{candidate_id}"))
            )
            champion_payload, champ_err = safe_api_call(
                lambda client: client.get(api_v1_path(f"/evaluations/{champion_id}"))
            )

            if cand_err:
                st.error(f"Candidate fetch error: {cand_err}")
            if champ_err:
                st.error(f"Champion fetch error: {champ_err}")

            if not cand_err and not champ_err:
                candidate_payload = candidate_payload or {}
                champion_payload = champion_payload or {}

                cand_metrics = _metric_dataframe(candidate_payload)
                champ_metrics = _metric_dataframe(champion_payload)

                # --- Metric comparison table ---
                if not cand_metrics.empty:
                    st.subheader("Metric comparison")
                    display_df = cand_metrics.copy()
                    display_df["status_label"] = display_df["delta"].map(_delta_status_label)
                    st.dataframe(
                        display_df[["metric", "champion", "candidate", "delta", "status_label"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "champion": st.column_config.NumberColumn(format="%.4f"),
                            "candidate": st.column_config.NumberColumn(format="%.4f"),
                            "delta": st.column_config.NumberColumn(format="%.4f"),
                        },
                    )

                    # --- Charts ---
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        st.plotly_chart(comparison_bar_chart(cand_metrics, champ_metrics), use_container_width=True)
                    with chart_col2:
                        st.plotly_chart(delta_bar_chart(cand_metrics), use_container_width=True)

                    st.plotly_chart(radar_comparison_chart(cand_metrics, champ_metrics), use_container_width=True)

                # --- Slice comparison ---
                cand_slices = _slice_dataframe(candidate_payload)
                champ_slices = _slice_dataframe(champion_payload)

                if not cand_slices.empty and not champ_slices.empty:
                    st.subheader("Slice-by-slice comparison")
                    # Merge slices on slice name
                    merged = cand_slices.merge(
                        champ_slices,
                        on="slice",
                        suffixes=("_candidate", "_champion"),
                        how="outer",
                    )
                    if "delta_candidate" in merged.columns:
                        merged["delta"] = merged["delta_candidate"]
                    elif "delta" in merged.columns:
                        pass
                    else:
                        merged["delta"] = 0.0

                    slice_df = merged[["slice", "delta"]].copy()
                    slice_df = slice_df.dropna(subset=["delta"])
                    if not slice_df.empty:
                        st.plotly_chart(slice_delta_heatmap(slice_df), use_container_width=True)

                # --- Performance comparison ---
                st.subheader("Performance comparison")
                perf_col1, perf_col2 = st.columns(2)
                perf_col3 = st.columns(1)[0]
                perf_col1.metric(
                    "Duration (s)",
                    f"{candidate_payload.get('duration_seconds', 0.0):.2f}",
                    delta=f"{candidate_payload.get('duration_seconds', 0.0) - champion_payload.get('duration_seconds', 0.0):.2f}",
                )
                perf_col2.metric(
                    "Candidate F1",
                    f"{candidate_payload.get('overall_f1', 0.0):.3f}",
                    delta=f"{candidate_payload.get('overall_f1', 0.0) - champion_payload.get('overall_f1', 0.0):.3f}",
                )
                perf_col3.metric(
                    "Candidate Accuracy",
                    f"{candidate_payload.get('overall_accuracy', 0.0):.3f}",
                    delta=f"{candidate_payload.get('overall_accuracy', 0.0) - champion_payload.get('overall_accuracy', 0.0):.3f}",
                )

                # --- Recommendation ---
                st.markdown("---")
                st.subheader("Recommendation")
                st.markdown(_recommendation(candidate_payload, cand_metrics))

    maybe_auto_refresh()

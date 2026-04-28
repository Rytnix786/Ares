from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import api_v1_path, safe_api_call
from dashboard.components.charts import metric_delta_heatmap, slice_bar, slice_delta_heatmap
from dashboard.components.connection_status import ensure_api_connection


def _narrative_box(payload: dict) -> None:
    narrative = payload.get("decision_narrative") or payload.get("failure_reason") or "No decision narrative available."
    if payload.get("passed"):
        st.success(narrative)
    else:
        st.error(narrative)


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

if ensure_api_connection():
    st.title("Drill Down")
    run_id = st.query_params.get("run_id", "")
    if not run_id:
        st.info("Select a run from the leaderboard or open a dashboard details URL.")
    else:
        payload, error = safe_api_call(lambda client: client.get(api_v1_path(f"/evaluations/{run_id}")))
        if error:
            if "404" in error:
                st.warning("Run not found. Select a different evaluation from the leaderboard.")
            else:
                st.error(error)
        else:
            payload = payload or {}
            _narrative_box(payload)
            st.subheader(f"Run {run_id}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Decision", "PASS" if payload.get("passed") else "FAIL")
            col2.metric("F1", f"{payload.get('overall_f1', 0.0):.3f}")
            col3.metric("Accuracy", f"{payload.get('overall_accuracy', 0.0):.3f}")
            col4.metric("Duration (s)", f"{payload.get('duration_seconds', 0.0):.2f}")

            if payload.get("artifact_uri"):
                st.link_button("View in MLflow", payload["artifact_uri"])

            metrics_df = _metric_dataframe(payload)
            if not metrics_df.empty:
                st.subheader("Metric comparison")
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)
                st.plotly_chart(metric_delta_heatmap(metrics_df), use_container_width=True)

            slice_df = _slice_dataframe(payload)
            if not slice_df.empty:
                st.subheader("Slice breakdown")
                left, right = st.columns(2)
                left.plotly_chart(slice_bar(slice_df), use_container_width=True)
                right.plotly_chart(slice_delta_heatmap(slice_df), use_container_width=True)

            config_payload, config_error = safe_api_call(lambda client: client.get(api_v1_path("/gate/config")))
            with st.expander("What if? threshold simulation", expanded=False):
                if config_error:
                    st.error(config_error)
                else:
                    config_payload = config_payload or {}
                    max_regression_f1 = st.slider(
                        "max_regression_f1",
                        min_value=0.0,
                        max_value=0.1,
                        value=float(config_payload.get("max_regression_f1", 0.02)),
                        step=0.005,
                    )
                    critical_slice_min_f1 = st.slider(
                        "critical_slice_min_f1",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(config_payload.get("critical_slice_min_f1", 0.60)),
                        step=0.01,
                    )
                    if st.button("Run simulation", type="primary"):
                        simulation_payload, simulation_error = safe_api_call(
                            lambda client: client.post(
                                api_v1_path("/gate/simulate"),
                                json={
                                    "run_id": run_id,
                                    "override_thresholds": {
                                        "max_regression_f1": max_regression_f1,
                                        "critical_slice_min_f1": critical_slice_min_f1,
                                    },
                                },
                            )
                        )
                        if simulation_error:
                            st.error(simulation_error)
                        else:
                            simulation_payload = simulation_payload or {}
                            st.write(simulation_payload.get("decision_narrative", ""))
                            sim_metrics_df = _metric_dataframe(simulation_payload)
                            if not sim_metrics_df.empty:
                                st.dataframe(sim_metrics_df, use_container_width=True, hide_index=True)
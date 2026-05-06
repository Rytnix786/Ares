from __future__ import annotations

# ruff: noqa: E402
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.api_client import api_v1_path, get_slice_trends, safe_api_call
from dashboard.components.charts import kl_trend_line, slice_metric_trend_line
from dashboard.components.connection_status import ensure_api_connection
from dashboard.components.real_time_metrics import (
    auto_refresh_sidebar_controls,
    maybe_auto_refresh,
    refresh_button,
)
from dashboard.components.state_handlers import data_state_check, empty_state


def _psi_color(psi: float) -> str:
    if psi < 0.1:
        return "#16a34a"
    if psi <= 0.2:
        return "#d97706"
    return "#dc2626"

auto_refresh_sidebar_controls()

if ensure_api_connection():
    st.title("Drift Monitor")
    refresh_button()
    payload, error = safe_api_call(lambda client: client.get(api_v1_path("/drift/reports")))
    if not data_state_check(
        payload,
        error,
        empty_message="No drift data yet. Run `python scripts/run_drift_check.py --help` to generate your first report.",
        empty_icon="📉",
    ):
        maybe_auto_refresh()
        st.stop()
    df = pd.DataFrame(payload)
    if df.empty:
        empty_state("No drift data yet. Run `python scripts/run_drift_check.py --help` to generate your first report.", icon="📉")
        maybe_auto_refresh()
        st.stop()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    latest = df.sort_values("created_at", ascending=False).groupby("feature", as_index=False).first()

    st.subheader("Latest PSI by feature")
    columns = st.columns(max(1, min(3, len(latest))))
    for idx, (_, row) in enumerate(latest.iterrows()):
        with columns[idx % len(columns)]:
            st.markdown(
                f"""
                <div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-bottom:12px;">
                    <div style="font-size:0.9rem;color:#6b7280;">{row['feature']}</div>
                    <div style="font-size:1.8rem;font-weight:700;color:{_psi_color(float(row['psi']))};">{float(row['psi']):.3f}</div>
                    <div style="font-size:0.85rem;color:#6b7280;">severity: {row['severity']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    tab_reports, tab_slice_trends = st.tabs(["Drift reports", "Slice trends"])
    with tab_reports:
        st.plotly_chart(kl_trend_line(df), use_container_width=True)
        st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)

    with tab_slice_trends:
        model_options = ["All models"] + sorted(df["model_name"].dropna().unique().tolist())
        selected_model = st.selectbox("Model filter", model_options, key="slice_trend_model")
        trends_payload, trends_error = get_slice_trends(None if selected_model == "All models" else selected_model)
        if trends_error:
            st.error(trends_error)
        else:
            trend_df = pd.DataFrame(trends_payload or [])
            if trend_df.empty:
                empty_state("No slice trend points yet. Slice trend retention is active once evaluations record slice metrics.", icon="📈")
            else:
                trend_df["window_start"] = pd.to_datetime(trend_df["window_start"], errors="coerce")
                st.plotly_chart(slice_metric_trend_line(trend_df), use_container_width=True)
                st.dataframe(trend_df.sort_values("window_start", ascending=False), use_container_width=True, hide_index=True)
    maybe_auto_refresh()

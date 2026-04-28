from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import api_v1_path, safe_api_call
from dashboard.components.charts import kl_trend_line
from dashboard.components.connection_status import ensure_api_connection


def _psi_color(psi: float) -> str:
    if psi < 0.1:
        return "#16a34a"
    if psi <= 0.2:
        return "#d97706"
    return "#dc2626"

if ensure_api_connection():
    st.title("Drift Monitor")
    payload, error = safe_api_call(lambda client: client.get(api_v1_path("/drift/reports")))
    if error:
        st.error(error)
    else:
        df = pd.DataFrame(payload or [])
        if df.empty:
            st.info("No drift data yet. Run `python scripts/run_drift_check.py --help` to generate your first report.")
        else:
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

            st.plotly_chart(kl_trend_line(df), use_container_width=True)
            st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)
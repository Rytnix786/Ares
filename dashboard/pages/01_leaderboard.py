from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import api_v1_path, safe_api_call
from dashboard.components.charts import f1_line
from dashboard.components.connection_status import ensure_api_connection


def _status_badge(passed: bool) -> str:
    return "✅ PASS" if passed else "❌ FAIL"


if ensure_api_connection():
    st.title("Leaderboard")
    payload, error = safe_api_call(lambda client: client.get(api_v1_path("/evaluations/")))
    if error:
        st.error(error)
    else:
        df = pd.DataFrame(payload or [])
        if df.empty:
            st.info("No evaluations yet. Run your first evaluation with: `python scripts/run_evaluation.py --help`")
        else:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
            model_names = sorted(name for name in df["model_name"].dropna().unique().tolist())
            with st.sidebar:
                st.subheader("Filters")
                selected_models = st.multiselect("Model name", options=model_names, default=model_names)
                min_date = df["created_at"].min().date()
                max_date = df["created_at"].max().date()
                date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

                with st.expander("Champion History", expanded=False):
                    if not model_names:
                        st.caption("No models available yet.")
                    else:
                        history_model = st.selectbox("Model", options=model_names, index=0)
                        history_payload, history_error = safe_api_call(
                            lambda client: client.get(api_v1_path(f"/champions/{history_model}/history"))
                        )
                        if history_error:
                            st.error(history_error)
                        else:
                            history_payload = history_payload or {}
                            history_df = pd.DataFrame(history_payload.get("history", []))
                            if history_df.empty:
                                st.caption("No champion history recorded yet.")
                            else:
                                history_df["label"] = history_df.apply(
                                    lambda row: f"{'🏆 ' if row.get('is_active') else ''}{row.get('promoted_at', '')} · {row.get('champion_run_id', '')}",
                                    axis=1,
                                )
                                st.dataframe(
                                    history_df[["label", "promoted_by", "promotion_reason"]],
                                    use_container_width=True,
                                    hide_index=True,
                                )

            filtered = df.copy()
            if selected_models:
                filtered = filtered[filtered["model_name"].isin(selected_models)]
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
                filtered = filtered[
                    (filtered["created_at"].dt.date >= start_date.date())
                    & (filtered["created_at"].dt.date <= end_date.date())
                ]

            filtered = filtered.sort_values("created_at", ascending=False)
            filtered["status"] = filtered["passed"].map(_status_badge)
            filtered["champion"] = filtered["is_current_champion"].map(lambda value: "🏆" if value else "")

            st.plotly_chart(f1_line(df), use_container_width=True)
            st.dataframe(
                filtered[
                    [
                        "champion",
                        "status",
                        "model_name",
                        "model_version",
                        "overall_f1",
                        "overall_accuracy",
                        "commit_sha",
                        "created_at",
                        "id",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
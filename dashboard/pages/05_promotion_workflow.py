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
from dashboard.components.connection_status import ensure_api_connection
from dashboard.components.real_time_metrics import (
    auto_refresh_sidebar_controls,
    maybe_auto_refresh,
    refresh_button,
)


def _risk_assessment(delta: float) -> tuple[str, str]:
    """Return (risk_level, color) based on delta magnitude."""
    abs_delta = abs(delta)
    if abs_delta > 0.05:
        return "High", "#dc2626"
    if abs_delta > 0.02:
        return "Medium", "#d97706"
    return "Low", "#16a34a"


auto_refresh_sidebar_controls()

if ensure_api_connection():
    st.title("Promotion Workflow")
    refresh_button()

    tab_candidates, tab_pending, tab_history = st.tabs(["Candidate Runs", "Pending Promotions", "Promotion History"])

    # --- Tab 1: Candidate Runs that passed gate ---
    with tab_candidates:
        evals_payload, evals_error = safe_api_call(
            lambda client: client.get(api_v1_path("/evaluations/"))
        )
        if evals_error:
            st.error(evals_error)
        else:
            evals = evals_payload or []
            df = pd.DataFrame(evals)
            if df.empty:
                st.info("No evaluation runs available yet.")
            else:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
                # Filter to runs that passed the gate
                passed = df[df["passed"] == True].copy()  # noqa: E712
                if passed.empty:
                    st.info("No candidate runs have passed the gate yet.")
                else:
                    passed = passed.sort_values("created_at", ascending=False)

                    # Get current champions for comparison
                    export_payload, export_error = safe_api_call(
                        lambda client: client.get(api_v1_path("/champions/export"))
                    )
                    champions_map: dict[str, dict] = {}
                    if not export_error and export_payload:
                        for entry in export_payload.get("champions", []):
                            champions_map[entry["model_name"]] = entry

                    st.subheader("Candidates that passed the gate")
                    for _, row in passed.iterrows():
                        model_name = row.get("model_name", "")
                        run_id = row.get("id", "")
                        is_champion = row.get("is_current_champion", False)

                        with st.container():
                            col_info, col_action = st.columns([3, 1])
                            with col_info:
                                badge = "🏆 Current Champion" if is_champion else "✅ Passed Gate"
                                st.markdown(f"**{badge}** — `{model_name}` v{row.get('model_version', '')}")
                                st.caption(
                                    f"Run `{run_id[:8]}` · F1 {row.get('overall_f1', 0.0):.3f} · "
                                    f"Accuracy {row.get('overall_accuracy', 0.0):.3f} · "
                                    f"Created {row.get('created_at', '')}"
                                )
                                # Show risk assessment based on delta vs champion
                                champion_entry = champions_map.get(model_name)
                                if champion_entry and champion_entry.get("evaluation"):
                                    champ_f1 = champion_entry["evaluation"].get("metrics", {}).get("overall_f1", 0.0)
                                    delta_f1 = row.get("overall_f1", 0.0) - champ_f1
                                    risk_level, risk_color = _risk_assessment(delta_f1)
                                    st.markdown(
                                        f'<span style="color:{risk_color};font-weight:600;">Risk: {risk_level}</span>'
                                        f' · Δ F1 = {delta_f1:+.4f} vs current champion',
                                        unsafe_allow_html=True,
                                    )
                            with col_action:
                                if not is_champion:
                                    if st.button("Promote", key=f"promote_{run_id}", type="primary"):
                                        st.session_state[f"show_promote_form_{run_id}"] = True

                            # Show promotion form if triggered
                            if st.session_state.get(f"show_promote_form_{run_id}", False):
                                with st.form(f"promote_form_{run_id}"):
                                    st.markdown(f"**Promote `{model_name}` run `{run_id[:8]}`**")
                                    promoted_by = st.text_input("Your name", value="", key=f"promoted_by_{run_id}")
                                    reason = st.text_area("Reason for promotion", value="", key=f"reason_{run_id}")
                                    submitted = st.form_submit_button("Confirm Promotion")
                                    cancelled = st.form_submit_button("Cancel")
                                    if cancelled:
                                        st.session_state[f"show_promote_form_{run_id}"] = False
                                        st.rerun()
                                    if submitted:
                                        if not promoted_by.strip():
                                            st.error("Please enter your name.")
                                        else:
                                            result, err = safe_api_call(
                                                lambda client, mn=model_name, rid=run_id, pb=promoted_by, r=reason: client.post(
                                                    api_v1_path(f"/champions/{mn}/promote"),
                                                    json={"run_id": rid, "promoted_by": pb, "reason": r or None},
                                                )
                                            )
                                            if err:
                                                st.error(f"Promotion failed: {err}")
                                            else:
                                                st.session_state[f"show_promote_form_{run_id}"] = False
                                                st.success(f"Successfully promoted `{model_name}` to run `{run_id[:8]}`")
                                                st.rerun()

    # --- Tab 2: Pending Promotions Queue ---
    with tab_pending:
        st.subheader("Pending promotions")
        st.caption("Runs that passed the gate but are not yet champion.")
        evals_payload2, evals_error2 = safe_api_call(
            lambda client: client.get(api_v1_path("/evaluations/"))
        )
        if evals_error2:
            st.error(evals_error2)
        else:
            evals2 = evals_payload2 or []
            df2 = pd.DataFrame(evals2)
            if df2.empty:
                st.info("No evaluations available.")
            else:
                df2["created_at"] = pd.to_datetime(df2["created_at"], errors="coerce")
                pending = df2[(df2["passed"] == True) & (df2["is_current_champion"] == False)].copy()  # noqa: E712
                if pending.empty:
                    st.success("No pending promotions — all passed runs are already champion or no runs have passed.")
                else:
                    pending = pending.sort_values("created_at", ascending=False)
                    st.dataframe(
                        pending[["model_name", "model_version", "overall_f1", "overall_accuracy", "created_at", "id"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "id": st.column_config.TextColumn("Run ID"),
                            "overall_f1": st.column_config.NumberColumn("F1", format="%.4f"),
                            "overall_accuracy": st.column_config.NumberColumn("Accuracy", format="%.4f"),
                        },
                    )

    # --- Tab 3: Promotion History with Rollback ---
    with tab_history:
        st.subheader("Promotion history")
        # Get all model names
        evals_payload3, evals_error3 = safe_api_call(
            lambda client: client.get(api_v1_path("/evaluations/"))
        )
        if evals_error3:
            st.error(evals_error3)
        else:
            evals3 = evals_payload3 or []
            df3 = pd.DataFrame(evals3)
            if df3.empty:
                st.info("No evaluation data available.")
            else:
                model_names = sorted(name for name in df3["model_name"].dropna().unique().tolist())
                if not model_names:
                    st.info("No models found.")
                else:
                    selected_model = st.selectbox("Select model", options=model_names, key="history_model")
                    history_payload, history_error = safe_api_call(
                        lambda client: client.get(api_v1_path(f"/champions/{selected_model}/history"))
                    )
                    if history_error:
                        st.error(history_error)
                    else:
                        history_payload = history_payload or {}
                        history_entries = history_payload.get("history", [])
                        if not history_entries:
                            st.info(f"No promotion history for `{selected_model}`.")
                        else:
                            history_df = pd.DataFrame(history_entries)
                            history_df["promoted_at"] = pd.to_datetime(history_df["promoted_at"], errors="coerce")
                            history_df = history_df.sort_values("promoted_at", ascending=False)

                            for _, entry in history_df.iterrows():
                                is_active = entry.get("is_active", False)
                                status_icon = "🏆 Active" if is_active else "⏪ Inactive"
                                with st.container():
                                    col_h1, col_h2 = st.columns([4, 1])
                                    with col_h1:
                                        st.markdown(
                                            f"**{status_icon}** — Run `{entry.get('champion_run_id', '')[:8]}` · "
                                            f"Promoted by `{entry.get('promoted_by', '')}` at `{entry.get('promoted_at', '')}`"
                                        )
                                        if entry.get("promotion_reason"):
                                            st.caption(f"Reason: {entry['promotion_reason']}")
                                    with col_h2:
                                        if not is_active:
                                            if st.button("Rollback", key=f"rollback_{entry.get('id', '')}"):
                                                st.session_state[f"show_rollback_{entry.get('id', '')}"] = True

                                # Rollback confirmation
                                if st.session_state.get(f"show_rollback_{entry.get('id', '')}", False):
                                    with st.form(f"rollback_form_{entry.get('id', '')}"):
                                        st.warning(
                                            f"Rollback `{selected_model}` to run `{entry.get('champion_run_id', '')[:8]}`?"
                                        )
                                        rollback_by = st.text_input("Your name", value="", key=f"rollback_by_{entry.get('id', '')}")
                                        rollback_reason = st.text_area("Reason for rollback", value="", key=f"rollback_reason_{entry.get('id', '')}")
                                        confirm = st.form_submit_button("Confirm Rollback")
                                        cancel_rb = st.form_submit_button("Cancel")
                                        if cancel_rb:
                                            st.session_state[f"show_rollback_{entry.get('id', '')}"] = False
                                            st.rerun()
                                        if confirm:
                                            if not rollback_by.strip():
                                                st.error("Please enter your name.")
                                            else:
                                                # Rollback = promote the previous champion's run_id
                                                result_rb, err_rb = safe_api_call(
                                                    lambda client, mn=selected_model, rid=entry.get("champion_run_id", ""), pb=rollback_by, r=rollback_reason: client.post(
                                                        api_v1_path(f"/champions/{mn}/promote"),
                                                        json={"run_id": rid, "promoted_by": pb, "reason": f"Rollback: {r}" or "Rollback"},
                                                    )
                                                )
                                                if err_rb:
                                                    st.error(f"Rollback failed: {err_rb}")
                                                else:
                                                    st.session_state[f"show_rollback_{entry.get('id', '')}"] = False
                                                    st.success(f"Successfully rolled back `{selected_model}` to run `{entry.get('champion_run_id', '')[:8]}`")
                                                    st.rerun()

    maybe_auto_refresh()

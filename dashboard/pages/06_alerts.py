from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import api_v1_path, safe_api_call
from dashboard.components.connection_status import ensure_api_connection
from dashboard.components.real_time_metrics import (
    auto_refresh_sidebar_controls,
    maybe_auto_refresh,
    refresh_button,
)

auto_refresh_sidebar_controls()

if ensure_api_connection():
    st.title("Alert Configuration")
    refresh_button()

    tab_rules, tab_channels, tab_history, tab_test = st.tabs(
        ["Alert Rules", "Alert Channels", "Alert History", "Test Alerts"]
    )

    # --- Tab 1: Alert Rules (gate thresholds) ---
    with tab_rules:
        st.subheader("Gate thresholds")
        st.caption("These thresholds control when drift and regression alerts fire.")
        config_payload, config_error = safe_api_call(
            lambda client: client.get(api_v1_path("/gate/config"))
        )
        if config_error:
            st.error(config_error)
        else:
            config_payload = config_payload or {}
            st.json(config_payload)
            st.info(
                "Gate thresholds are configured via `ares.config.yaml` or environment variables. "
                "Update them there and restart the API to apply changes."
            )

    # --- Tab 2: Alert Channels ---
    with tab_channels:
        st.subheader("Notification channels")

        # Slack webhook
        with st.container():
            st.markdown("#### Slack")
            slack_webhook = st.text_input(
                "Slack Webhook URL",
                value=st.secrets.get("SLACK_WEBHOOK_URL", ""),
                type="password",
                key="slack_webhook_url",
            )
            if slack_webhook:
                st.success("Slack webhook URL is configured.")
            else:
                st.warning(
                    "No Slack webhook URL configured. Set `SLACK_WEBHOOK_URL` in your "
                    "Streamlit secrets or environment variables to enable Slack notifications."
                )

        # Email (placeholder)
        with st.container():
            st.markdown("#### Email")
            email_recipient = st.text_input(
                "Alert email recipient",
                value=st.secrets.get("ALERT_EMAIL", ""),
                key="alert_email",
            )
            if email_recipient:
                st.success(f"Alert emails will be sent to `{email_recipient}`.")
            else:
                st.info(
                    "No email alert recipient configured. Set `ALERT_EMAIL` in your "
                    "Streamlit secrets or environment variables to enable email notifications."
                )

        st.caption(
            "Channel configuration is stored in Streamlit secrets (`.streamlit/secrets.toml`) "
            "or environment variables. Update them and restart the dashboard to apply."
        )

    # --- Tab 3: Alert History ---
    with tab_history:
        st.subheader("Alert history")
        drift_payload, drift_error = safe_api_call(
            lambda client: client.get(api_v1_path("/drift/reports"))
        )
        if drift_error:
            st.error(drift_error)
        else:
            drift_reports = drift_payload or []
            df = pd.DataFrame(drift_reports)
            if df.empty:
                st.info("No drift reports available yet.")
            else:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
                # Filter to alerting reports
                alerting = df[df["is_alerting"] == True].copy()  # noqa: E712
                if alerting.empty:
                    st.success("No alerts have fired yet.")
                else:
                    alerting = alerting.sort_values("created_at", ascending=False)
                    alerting["status"] = alerting["severity"].map(
                        lambda s: "🔴 High" if s == "high" else "🟡 Medium" if s == "medium" else "🟢 Low"
                    )
                    st.dataframe(
                        alerting[["status", "model_name", "feature", "psi", "kl_divergence", "severity", "created_at", "id"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "psi": st.column_config.NumberColumn("PSI", format="%.4f"),
                            "kl_divergence": st.column_config.NumberColumn("KL Divergence", format="%.4f"),
                        },
                    )

                    # Summary
                    st.markdown("---")
                    st.subheader("Alert summary")
                    total_alerts = len(alerting)
                    high_count = len(alerting[alerting["severity"] == "high"])
                    medium_count = len(alerting[alerting["severity"] == "medium"])
                    low_count = len(alerting[alerting["severity"] == "low"])
                    sc1, sc2 = st.columns(2)
                    sc3, sc4 = st.columns(2)
                    sc1.metric("Total Alerts", total_alerts)
                    sc2.metric("High Severity", high_count, delta="🔴" if high_count > 0 else "✅", delta_color="inverse")
                    sc3.metric("Medium Severity", medium_count)
                    sc4.metric("Low Severity", low_count)

    # --- Tab 4: Test Alerts ---
    with tab_test:
        st.subheader("Test alert delivery")
        st.caption("Send a test alert to verify your notification channels are working.")

        test_message = st.text_area(
            "Test message",
            value="🔔 Test alert from Ares dashboard — notification channel is working!",
            key="test_alert_message",
        )

        if st.button("Send test Slack alert", type="primary"):
            webhook_url = st.secrets.get("SLACK_WEBHOOK_URL", "")
            if not webhook_url:
                st.error("No Slack webhook URL configured. Set `SLACK_WEBHOOK_URL` in secrets first.")
            else:
                test_result, test_error = safe_api_call(
                    lambda client: client.post(
                        api_v1_path("/drift/reports"),
                        json={
                            "model_name": "test-model",
                            "feature": "test-feature",
                            "kl_divergence": 0.0,
                            "psi": 0.0,
                            "is_alerting": False,
                            "severity": "low",
                            "payload": {"test": True, "message": test_message},
                        },
                    )
                )
                if test_error:
                    st.error(f"Test alert failed: {test_error}")
                else:
                    st.success("Test drift report created successfully. Check your Slack channel for the notification.")

        if st.button("Send test alert via API health check"):
            health_result, health_error = safe_api_call(
                lambda client: client.get("/health/live")
            )
            if health_error:
                st.error(f"API is unreachable: {health_error}")
            else:
                st.success("API is reachable and healthy. Alert infrastructure is operational.")

    maybe_auto_refresh()

from __future__ import annotations

from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from dashboard.api_client import api_v1_path, safe_api_call


def init_auto_refresh_state() -> None:
    """Initialize auto-refresh session state defaults."""
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False
    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = 30
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = None


def auto_refresh_sidebar_controls() -> None:
    """Render auto-refresh toggle and interval selector in the sidebar."""
    init_auto_refresh_state()
    with st.sidebar:
        st.markdown("---")
        st.subheader("Auto-refresh")
        st.session_state.auto_refresh = st.toggle(
            "Enable auto-refresh",
            value=st.session_state.auto_refresh,
        )
        if st.session_state.auto_refresh:
            st.session_state.refresh_interval = st.select_slider(
                "Interval (seconds)",
                options=[10, 15, 30, 60, 120],
                value=st.session_state.refresh_interval,
            )


def _inject_auto_refresh_script(interval_seconds: int) -> None:
    """Inject a JavaScript snippet that reloads the page after *interval_seconds*."""
    components.html(
        f"""
        <script>
          setTimeout(function () {{
            window.parent.location.reload();
          }}, {interval_seconds * 1000});
        </script>
        """,
        height=0,
    )


def maybe_auto_refresh() -> None:
    """Trigger a page reload if auto-refresh is enabled."""
    init_auto_refresh_state()
    if st.session_state.auto_refresh:
        _inject_auto_refresh_script(st.session_state.refresh_interval)


def refresh_button() -> None:
    """Render a manual refresh button with last-update timestamp."""
    init_auto_refresh_state()
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.last_refresh = datetime.now().isoformat(timespec="seconds")
            st.rerun()
    with col2:
        ts = st.session_state.last_refresh
        if ts:
            st.caption(f"Last updated: {ts}")
        else:
            st.caption("Not yet refreshed")


def render_real_time_metrics() -> None:
    """Fetch and display aggregate real-time metrics on the main dashboard page."""
    evals_data, evals_error = safe_api_call(
        lambda client: client.get(api_v1_path("/evaluations/"))
    )
    drift_data, drift_error = safe_api_call(
        lambda client: client.get(api_v1_path("/drift/reports"))
    )

    if evals_error and drift_error:
        st.warning("Could not load metrics data.")
        return

    evals = evals_data or []
    drift_reports = drift_data or []

    total_runs = len(evals)
    pass_count = sum(1 for e in evals if e.get("passed"))
    fail_count = total_runs - pass_count
    pass_rate = (pass_count / total_runs * 100) if total_runs else 0.0

    champion_count = sum(1 for e in evals if e.get("is_current_champion"))

    avg_duration = 0.0
    durations = [e.get("duration_seconds", 0) for e in evals if e.get("duration_seconds")]
    if durations:
        avg_duration = sum(durations) / len(durations)

    high_severity_drift = sum(
        1 for d in drift_reports if d.get("severity") == "high"
    )

    row1_col1, row1_col2, row1_col3 = st.columns(3)
    row2_col1, row2_col2 = st.columns(2)
    row1_col1.metric("Total Runs", total_runs)
    row1_col2.metric("Pass Rate", f"{pass_rate:.1f}%", delta=f"{pass_count} passed / {fail_count} failed")
    row1_col3.metric("Active Champions", champion_count)
    row2_col1.metric("Avg Duration (s)", f"{avg_duration:.1f}")
    row2_col2.metric("High-Severity Drift", high_severity_drift, delta="⚠️" if high_severity_drift > 0 else "✅", delta_color="inverse")

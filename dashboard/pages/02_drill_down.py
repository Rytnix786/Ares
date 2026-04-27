from __future__ import annotations

import streamlit as st

from dashboard.api_client import safe_api_call
from dashboard.components.connection_status import ensure_api_connection

if ensure_api_connection():
    st.title("Drill Down")
    run_id = st.query_params.get("run_id", "")
    if not run_id:
        st.info("Select a run from the leaderboard or open a dashboard details URL.")
    else:
        payload, error = safe_api_call(lambda client: client.get(f"/evaluations/{run_id}"))
        if error:
            st.error(error)
        else:
            st.subheader(f"Run {run_id}")
            st.json(payload)
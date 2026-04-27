from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import safe_api_call
from dashboard.components.charts import f1_line
from dashboard.components.connection_status import ensure_api_connection

if ensure_api_connection():
    st.title("Leaderboard")
    payload, error = safe_api_call(lambda client: client.get("/evaluations/"))
    if error:
        st.error(error)
    else:
        df = pd.DataFrame(payload or [])
        if df.empty:
            st.info("No evaluation runs available yet.")
        else:
            st.plotly_chart(f1_line(df), use_container_width=True)
            st.dataframe(df, use_container_width=True)
from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import safe_api_call
from dashboard.components.connection_status import ensure_api_connection

if ensure_api_connection():
    st.title("Drift Monitor")
    payload, error = safe_api_call(lambda client: client.get("/drift/reports"))
    if error:
        st.error(error)
    else:
        df = pd.DataFrame(payload or [])
        if df.empty:
            st.info("Drift reports will appear here once generated.")
        else:
            st.dataframe(df, use_container_width=True)
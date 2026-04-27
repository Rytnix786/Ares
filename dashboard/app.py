from __future__ import annotations

import streamlit as st

from dashboard.components.connection_status import ensure_api_connection

st.set_page_config(page_title="Ares", layout="wide")
if ensure_api_connection():
    st.title("Ares — Model Regression Detection")
    st.write("Use the pages sidebar for leaderboard, drill-down, and drift monitoring.")
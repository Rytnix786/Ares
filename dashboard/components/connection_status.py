from __future__ import annotations

import time

import streamlit as st
import streamlit.components.v1 as components

from dashboard.api_client import safe_api_call


def ensure_api_connection() -> bool:
    data, error = safe_api_call(lambda client: client.get("/health/live"))
    if error:
        st.title("Connecting to Ares API…")
        st.error(error)
        st.caption("The dashboard will auto-refresh every 30 seconds while the API is unavailable.")
        if st.button("Retry now"):
            st.rerun()
        components.html(
            """
            <script>
              setTimeout(function () {
                window.parent.location.reload();
              }, 30000);
            </script>
            """,
            height=0,
        )
        time.sleep(1)
        return False
    if isinstance(data, dict) and data.get("status") == "alive":
        return True
    st.warning("Unexpected health response from Ares API.")
    return False
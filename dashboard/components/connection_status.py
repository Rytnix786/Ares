from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from dashboard.api_client import get_api_base_url, get_api_key, safe_api_call


def ensure_api_connection() -> bool:
    with st.sidebar.expander("Connection settings", expanded=False):
        st.caption("Use the API root URL, for example `http://localhost:8000`.")
        st.text_input("ARES_API_URL", value=get_api_base_url(), key="ARES_API_URL")
        st.text_input("ARES_API_KEY", value=get_api_key(), key="ARES_API_KEY", type="password")

    data, error = safe_api_call(lambda client: client.get("/health/live"))
    if error:
        st.title("Connecting to Ares API…")
        st.error("Unable to connect to the Ares API.")
        with st.expander("Error details"):
            st.code(error)
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
        return False
    if isinstance(data, dict) and data.get("status") == "alive":
        return True
    st.warning("Unexpected health response from Ares API.")
    return False
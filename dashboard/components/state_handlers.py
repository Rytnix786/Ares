from __future__ import annotations

import streamlit as st


def empty_state(message: str, icon: str = "📭") -> None:
    """Render an empty state with an icon and message."""
    st.markdown(
        f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 48px 24px;
            text-align: center;
        ">
            <div style="font-size: 3rem; margin-bottom: 12px;">{icon}</div>
            <div style="font-size: 1.1rem; color: #6b7280; max-width: 400px;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def loading_state(message: str = "Loading data…") -> None:
    """Render a loading state with a spinner and message."""
    with st.spinner(message):
        st.empty()


def error_state(error_message: str, retry: bool = False) -> None:
    """Render an error state with optional retry button."""
    st.error(error_message)
    if retry:
        if st.button("🔄 Retry", key=f"retry_{hash(error_message)}"):
            st.rerun()


def network_error_state() -> None:
    """Render a network connectivity error state with retry."""
    error_state(
        "Unable to connect to the Ares API. Check your network connection and API URL.",
        retry=True,
    )


def data_state_check(
    data: object,
    error: str | None,
    empty_message: str = "No data available.",
    empty_icon: str = "📭",
    show_retry_on_error: bool = True,
) -> bool:
    """Handle the common data/error/empty pattern.

    Returns True if data is present and ready to use, False otherwise.
    Renders appropriate state components automatically.
    """
    if error:
        is_network = "Unable to connect" in error or "connect to Ares API" in error
        if is_network:
            network_error_state()
        else:
            error_state(error, retry=show_retry_on_error)
        return False

    if data is None or (hasattr(data, "__len__") and len(data) == 0):
        empty_state(empty_message, icon=empty_icon)
        return False

    return True

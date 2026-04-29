from __future__ import annotations

# ruff: noqa: E402
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from dashboard.components.connection_status import ensure_api_connection
from dashboard.components.real_time_metrics import (
    auto_refresh_sidebar_controls,
    maybe_auto_refresh,
    refresh_button,
    render_real_time_metrics,
)

st.set_page_config(page_title="Ares", layout="wide", initial_sidebar_state="expanded")

# Responsive CSS for mobile/tablet optimization
st.markdown(
    """
    <style>
    /* Responsive table scrolling */
    .stDataFrame {
        overflow-x: auto !important;
    }

    /* Smaller font on mobile */
    @media (max-width: 768px) {
        .stMarkdown, .stText {
            font-size: 0.9rem !important;
        }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.25rem !important; }
        h3 { font-size: 1.1rem !important; }
        .stMetricValue {
            font-size: 1.2rem !important;
        }
        .stMetricLabel {
            font-size: 0.75rem !important;
        }
        /* Collapse sidebar on mobile by default */
        [data-testid="stSidebar"] {
            min-width: 0 !important;
        }
    }

    /* Tablet adjustments */
    @media (min-width: 769px) and (max-width: 1024px) {
        .stMarkdown, .stText {
            font-size: 0.95rem !important;
        }
        .stMetricValue {
            font-size: 1.4rem !important;
        }
    }

    /* Horizontal scroll for wide dataframes */
    .stDataFrame table {
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

auto_refresh_sidebar_controls()

if ensure_api_connection():
    st.title("Ares — Model Regression Detection")
    refresh_button()
    render_real_time_metrics()
    st.markdown("---")
    st.write("Use the pages sidebar for leaderboard, drill-down, and drift monitoring.")
    maybe_auto_refresh()

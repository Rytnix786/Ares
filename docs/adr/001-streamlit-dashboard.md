+# ADR 001: Streamlit for Dashboard
+
+**Status:** Accepted  
+**Date:** 2026-01-01
+
+## Context
+
+Ares needs a dashboard for operators to review evaluation results,
+champion history, and drift reports.
+
+## Decision
+
+Use Streamlit rather than React/Next.js.
+
+## Reasons
+
+- Internal operator tool, not a public user-facing product
+- Python-native team — no separate JS build pipeline
+- Streamlit's data table and Plotly chart support covers all needs
+- Speed of iteration matters more than pixel-perfect custom layouts
+- Dashboard is not the core product — the gate engine is
+
+## Consequences
+
+- Dashboard cannot support real-time WebSocket updates natively
+- Complex URL routing requires `st.query_params`
+- Custom CSS is possible but discouraged
+- If product scope expands to a public SaaS, revisit this decision
+
+## Revisit When
+
+Dashboard needs real-time collaboration, complex routing, or public user accounts.
# Dashboard UX changes (execution log)

## 2026-04-27

### Connection UI (`dashboard/components/connection_status.py`)
- Added a **sidebar “Connection settings” expander** to set `ARES_API_URL` and `ARES_API_KEY` via `st.session_state` (no restart required).
- Improved the “API unavailable” state:
  - Clear top-level error message.
  - Full error details moved into an expander to reduce visual noise.
- Removed the unnecessary `time.sleep(1)` during the unavailable state.


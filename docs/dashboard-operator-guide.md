# Dashboard operator guide

The Streamlit dashboard is the primary operator console for day-to-day ARES workflows. Start it with:

```bash
streamlit run dashboard/app.py
```

Set `ARES_API_URL` and `ARES_API_KEY` in environment variables or Streamlit secrets. The dashboard accepts an API URL with or without `/api/v1`. API-key resolution order is: Streamlit session state, Streamlit secrets, `ARES_API_KEY`, first value from `ARES_API_KEYS`, then local development fallback `dev-key-1`. Protected deployments should always configure an explicit secret or environment key and should not rely on the local fallback.

## Recommended workflow

1. **Check connection status** from the landing page sidebar before taking action.
2. **Leaderboard**: scan recent runs and gate status.
3. **Model Comparison**: select candidate/champion runs, then use the N-way comparison selector to compare multiple candidates through `/api/v1/evaluations/compare`.
4. **Model card evidence**: open the candidate model-card expander before promotion to inspect generated model card metadata attached to the run.
5. **Promotion Workflow**: promote only passed runs, enter an actor and reason, and verify the current champion after success.
6. **Rollback**: use Promotion History rollback actions for governed rollback through `/api/v1/champions/{model}/rollback`. Always provide an operator reason.
7. **Drift Monitor**: review latest PSI/KL drift reports, then open Slice Trends to inspect subgroup metric movement through `/api/v1/slices/trends`.
8. **Alerts**: review alert history and test notification configuration after changing secrets or webhooks.

## UI state and safety conventions

- Promotion and rollback confirmations are stateful forms, not one-click mutations.
- Rollbacks call the first-class rollback API, preserving actor, reason, target run, and audit context.
- Empty states explain how to generate data instead of showing blank charts.
- Auto-refresh controls live in the sidebar and should be disabled during form entry if the operator is composing a long reason.

## Evidence to capture for release or incidents

- Screenshot of N-way comparison winner/risk summary.
- Screenshot or JSON export of the model-card evidence expander.
- Promotion or rollback success message with run ID and actor.
- Drift report table filtered to the affected model.
- Slice trend chart for the affected slice/key.
- Alert history row and external notification delivery evidence.

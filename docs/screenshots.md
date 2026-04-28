+# Screenshot Capture Guide
+
+Run the demo data seed first:
+
+```bash
+python scripts/seed_demo_data.py
+```
+
+Use browser dimensions **1440x900** for every capture.
+
+Save outputs to `docs/assets/screenshots/` using the filenames below.
+
+## Required screenshots
+
+1. **Leaderboard**
+   - Open `http://localhost:8501`
+   - Capture the leaderboard with a mix of pass/fail runs and a highlighted champion row
+   - Save as `leaderboard.png`
+
+2. **Drill-down**
+   - Open a failed run from the leaderboard
+   - Ensure the decision narrative is visible at the top
+   - Save as `drill-down-failed-run.png`
+
+3. **Drift monitor**
+   - Open the Drift Monitor page
+   - Capture an amber PSI card and the KL trend chart
+   - Save as `drift-monitor.png`
+
+4. **CLI output**
+   - Run `python scripts/run_evaluation.py --model-path models/candidate.json --commit-sha screenshot --model-name default-model --split val --output-json reports/ares_result.json`
+   - Capture the terminal plus `reports/ares_result.json`
+   - Save as `cli-output.png`
+
+5. **API docs**
+   - Open `http://localhost:8000/docs`
+   - Capture the FastAPI Swagger page
+   - Save as `api-docs.png`
+
+## Placeholder policy
+
+Add placeholders to the README immediately. Replace them with real screenshots after capture.
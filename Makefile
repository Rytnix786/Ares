PYTHON ?= python

.PHONY: dev lint test-unit test-integration test-e2e test test-all migrate migrate-down eval dashboard verify clean

dev:
	docker compose up -d

lint:
	ruff check . && mypy ares

test-unit:
	pytest -n auto -m "not integration and not e2e"

test-integration:
	pytest -m integration

test-e2e:
	pytest -m e2e

test:
	$(MAKE) test-unit && $(MAKE) test-integration && $(MAKE) test-e2e

test-all:
	pytest --tb=short --junitxml=reports/test-results.xml || true

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

eval:
	$(PYTHON) scripts/run_evaluation.py --model-path models/candidate.json --commit-sha local --model-name default-model --split val --output-json reports/ares_result.json

dashboard:
	streamlit run dashboard/app.py

verify:
	$(MAKE) lint && $(MAKE) test && docker compose config && dvc repro --dry && $(PYTHON) -m py_compile dashboard/app.py dashboard/pages/01_leaderboard.py dashboard/pages/02_drill_down.py dashboard/pages/03_drift_monitor.py

clean:
	$(PYTHON) -c "from pathlib import Path; [p.unlink() for pattern in ('reports/*.json','reports/*.html','reports/test-results.xml') for p in Path('.').glob(pattern) if p.exists()]"
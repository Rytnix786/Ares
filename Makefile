PYTHON ?= python

.PHONY: dev lint test-unit test-integration test-e2e test test-all migrate migrate-down eval dashboard verify clean

reports:
	mkdir -p reports

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
	pytest --cov=ares --cov-fail-under=90 --cov-report=term-missing

test-all: reports
	pytest --tb=short --cov=ares --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/test-results.xml

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

eval:
	$(PYTHON) scripts/run_evaluation.py --model-path models/candidate.json --commit-sha local --model-name default-model --split val --output-json reports/ares_result.json

dashboard:
	streamlit run dashboard/app.py

verify: reports
	ruff check . && mypy ares && pytest --cov=ares --cov-fail-under=90 --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/test-results.xml && docker compose config && dvc repro --dry && $(PYTHON) -m py_compile dashboard/app.py dashboard/pages/01_leaderboard.py dashboard/pages/02_drill_down.py dashboard/pages/03_drift_monitor.py

clean:
	$(PYTHON) -c "from pathlib import Path; [p.unlink() for pattern in ('reports/*.json','reports/*.html','reports/test-results.xml') for p in Path('.').glob(pattern) if p.exists()]"
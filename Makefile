PYTHON ?= python

.PHONY: benchmark build build-pkg clean dashboard dev eval lint migrate migrate-down test test-all test-e2e test-integration test-unit verify

reports:
	$(PYTHON) -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"

dev:
	docker compose up -d

build:
	docker compose build api worker dashboard
	@echo Build complete

build-pkg:
	$(PYTHON) -m build

lint:
	$(PYTHON) -m ruff check . && $(PYTHON) -m mypy ares

test-unit:
	$(PYTHON) -m pytest -n auto -m "not integration and not e2e"

test-integration:
	$(PYTHON) -m pytest -m integration

test-e2e:
	$(PYTHON) -m pytest -m e2e

test:
	$(PYTHON) -m pytest --cov=ares --cov-fail-under=90 --cov-report=term-missing

test-all: reports
	$(PYTHON) -m pytest --tb=short --cov=ares --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/test-results.xml

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

eval:
	$(PYTHON) scripts/run_evaluation.py --model-path models/candidate.json --commit-sha local --model-name default-model --split val --output-json reports/ares_result.json

dashboard:
	streamlit run dashboard/app.py

verify: reports
	$(PYTHON) scripts/verify_repo.py

benchmark:
	$(PYTHON) -m pytest tests/performance --benchmark-only -v

clean:
	$(PYTHON) -c "from pathlib import Path; [p.unlink() for pattern in ('reports/*.json','reports/*.html','reports/*.md','reports/*.txt','reports/*.db','reports/test-results.xml','reports/coverage.xml') for p in Path('.').glob(pattern) if p.exists()]"
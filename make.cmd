@echo off
setlocal

set "PYTHON=python"
set "TARGET=%~1"

if "%TARGET%"=="" goto :usage

if "%TARGET%"=="build" goto :build
if "%TARGET%"=="build-pkg" goto :build_pkg
if "%TARGET%"=="reports" goto :reports
if "%TARGET%"=="dev" goto :dev
if "%TARGET%"=="lint" goto :lint
if "%TARGET%"=="test-unit" goto :test_unit
if "%TARGET%"=="test-integration" goto :test_integration
if "%TARGET%"=="test-e2e" goto :test_e2e
if "%TARGET%"=="test" goto :test
if "%TARGET%"=="test-all" goto :test_all
if "%TARGET%"=="migrate" goto :migrate
if "%TARGET%"=="migrate-down" goto :migrate_down
if "%TARGET%"=="eval" goto :eval
if "%TARGET%"=="dashboard" goto :dashboard
if "%TARGET%"=="verify" goto :verify
if "%TARGET%"=="clean" goto :clean

echo Unknown target: %TARGET%
goto :usage

:build
docker compose build api worker dashboard
if errorlevel 1 exit /b %errorlevel%
echo Build complete
exit /b 0

:build_pkg
%PYTHON% -m build
exit /b %errorlevel%

:reports
%PYTHON% -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
exit /b %errorlevel%

:dev
docker compose up -d
exit /b %errorlevel%

:lint
%PYTHON% -m ruff check .
if errorlevel 1 exit /b %errorlevel%
%PYTHON% -m mypy ares
exit /b %errorlevel%

:test_unit
%PYTHON% -m pytest -n auto -m "not integration and not e2e"
exit /b %errorlevel%

:test_integration
%PYTHON% -m pytest -m integration
exit /b %errorlevel%

:test_e2e
%PYTHON% -m pytest -m e2e
exit /b %errorlevel%

:test
%PYTHON% -m pytest --cov=ares --cov-fail-under=90 --cov-report=term-missing
exit /b %errorlevel%

:test_all
call :reports
if errorlevel 1 exit /b %errorlevel%
%PYTHON% -m pytest --tb=short --cov=ares --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/test-results.xml
exit /b %errorlevel%

:migrate
%PYTHON% -m alembic upgrade head
exit /b %errorlevel%

:migrate_down
%PYTHON% -m alembic downgrade -1
exit /b %errorlevel%

:eval
%PYTHON% scripts\run_evaluation.py --model-path models/candidate.json --commit-sha local --model-name default-model --split val --output-json reports/ares_result.json
exit /b %errorlevel%

:dashboard
%PYTHON% -m streamlit run dashboard/app.py
exit /b %errorlevel%

:verify
call :reports
if errorlevel 1 exit /b %errorlevel%
%PYTHON% scripts\verify_repo.py
exit /b %errorlevel%

:clean
%PYTHON% -c "from pathlib import Path; [p.unlink() for pattern in ('reports/*.json','reports/*.html','reports/*.md','reports/*.txt','reports/*.db','reports/test-results.xml','reports/coverage.xml') for p in Path('.').glob(pattern) if p.exists()]"
exit /b %errorlevel%

:usage
echo Usage: make ^<target^>
echo Targets: build build-pkg reports dev lint test-unit test-integration test-e2e test test-all migrate migrate-down eval dashboard verify clean
exit /b 1
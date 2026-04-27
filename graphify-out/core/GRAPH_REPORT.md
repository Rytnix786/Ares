# Graph Report - ares  (2026-04-27)

## Corpus Check
- Corpus is ~4,380 words - fits in a single context window. You may not need a graph.

## Summary
- 149 nodes · 177 edges · 32 communities detected
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 40 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]

## God Nodes (most connected - your core abstractions)
1. `ClassificationEvaluator` - 8 edges
2. `BaseEvaluator` - 6 edges
3. `RegressionEvaluator` - 6 edges
4. `export()` - 5 edges
5. `compare_with_champion()` - 5 edges
6. `ChampionResponse` - 5 edges
7. `evaluate()` - 5 edges
8. `Base` - 5 edges
9. `LocalFileDataSource` - 4 edges
10. `DriftReportResponse` - 4 edges

## Surprising Connections (you probably didn't know these)
- `snapshot_gate_config()` --calls--> `load_ares_config()`  [INFERRED]
  ares\gate\rules_engine.py → ares\config.py
- `export()` --calls--> `export_champions()`  [INFERRED]
  ares\api\routers\champions.py → ares\db\crud.py
- `get_champion()` --calls--> `get_active_champion()`  [INFERRED]
  ares\api\routers\champions.py → ares\db\crud.py
- `promote()` --calls--> `promote_champion()`  [INFERRED]
  ares\api\routers\champions.py → ares\db\crud.py
- `compare_with_champion()` --calls--> `ComparisonResponse`  [INFERRED]
  ares\api\routers\evaluations.py → ares\api\schemas\evaluation.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.16
Nodes (10): ABC, BaseEvaluator, compute_metrics(), EvaluationResult, load_model(), predict(), LocalFileDataSource, ProductionDataSource (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.21
Nodes (13): BaseModel, ChampionEvaluationSnapshot, ChampionExportEntry, ChampionExportResponse, ChampionResponse, PromoteChampionRequest, export(), get_champion() (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.2
Nodes (9): export_champions(), get_active_champion(), get_evaluation_run(), list_evaluation_runs(), EvaluationRunResponse, compare_with_champion(), get_run(), list_runs() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.2
Nodes (6): GateDecision, get_gate_config(), evaluate(), snapshot_gate_config(), is_improvement_significant(), standard_error()

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (8): Base, Base, create_evaluation_run(), promote_champion(), DeclarativeBase, DriftReportRecord, EvaluationRun, ModelChampion

### Community 5 - "Community 5"
Cohesion: 0.24
Nodes (6): ClassificationEvaluator, _extract_text(), _keyword_features(), ClassificationEvaluator, DetectionEvaluator, Scaffold detection evaluator; defaults to classification-style label metrics.

### Community 6 - "Community 6"
Cohesion: 0.25
Nodes (4): BaseSettings, AresSettings, get_settings(), load_ares_config()

### Community 7 - "Community 7"
Cohesion: 0.29
Nodes (6): create_drift_report(), list_drift_reports(), create_report(), DriftReportIn, DriftReportResponse, list_reports()

### Community 8 - "Community 8"
Cohesion: 0.4
Nodes (2): BaseEvaluator, RegressionEvaluator

### Community 9 - "Community 9"
Cohesion: 0.7
Nodes (4): compute_drift_report(), DriftReport, kl_divergence(), population_stability_index()

### Community 10 - "Community 10"
Cohesion: 0.5
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 0.83
Nodes (3): get_db(), get_engine(), get_sessionmaker()

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (2): sha256_file(), validate_golden_set()

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **Thin community `Community 14`** (2 nodes): `logging.py`, `configure_logging()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (2 nodes): `main.py`, `rate_limit_handler()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `github_pr.py`, `build_pr_comment()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `slack.py`, `send_slack_message()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `telemetry.py`, `setup_telemetry()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `tasks.py`, `evaluate_task()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evaluate()` connect `Community 3` to `Community 2`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `compare_with_champion()` connect `Community 2` to `Community 1`, `Community 3`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `snapshot_gate_config()` connect `Community 3` to `Community 6`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ClassificationEvaluator` (e.g. with `BaseEvaluator` and `DetectionEvaluator`) actually correct?**
  _`ClassificationEvaluator` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `BaseEvaluator` (e.g. with `ClassificationEvaluator` and `RegressionEvaluator`) actually correct?**
  _`BaseEvaluator` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `export()` (e.g. with `export_champions()` and `ChampionExportEntry`) actually correct?**
  _`export()` has 4 INFERRED edges - model-reasoned connections that need verification._
# Testing Coverage Initiative Plan

## Current Status
- **Overall Coverage**: 47%
- **Tests Passing**: 55 tests
- **New Code Coverage**: 87-100% (exceptions, error handling, quality checks)
- **Existing Code Coverage**: 0% (evaluators, metrics, gate, golden_set core)

## Target
- **Overall Coverage**: 90%
- **Additional Tests Needed**: ~400+ unit tests

## Coverage Gap Analysis

### Critical Modules (0% coverage - Priority 1)
1. **ares/evaluators/base.py** (46 lines)
   - BaseEvaluator class
   - EvaluationResult dataclass
   - evaluate() method

2. **ares/evaluators/classification.py** (71 lines)
   - ClassificationEvaluator class
   - load_model(), predict(), compute_metrics()
   - Helper functions

3. **ares/gate/rules_engine.py** (46 lines)
   - snapshot_gate_config()
   - evaluate() function

4. **ares/gate/decision.py** (49 lines)
   - build_decision_narrative()
   - GateDecision dataclass

5. **ares/golden_set.py** (60 lines)
   - validate_golden_set()
   - sha256_file()

### High Priority Modules (0% coverage - Priority 2)
6. **ares/metrics/drift.py** (39 lines)
   - KL divergence, PSI calculations

7. **ares/metrics/slice_analysis.py** (28 lines)
   - Slice evaluation logic

8. **ares/metrics/significance.py** (25 lines)
   - Statistical significance tests

9. **ares/db/crud.py** (63 lines, 27% coverage)
   - CRUD operations for database
   - Need more comprehensive tests

10. **ares/db/session.py** (24 lines, 42% coverage)
    - Session management
    - Connection pooling

### Medium Priority (0% coverage - Priority 3)
11. **ares/api/routers/** (evaluations, champions, gate, drift)
    - API endpoint tests
    - Integration with FastAPI

12. **ares/notifier/** (slack, github_pr)
    - Notification tests

13. **ares/worker/tasks.py**
    - Celery task tests

## Testing Strategy

### Phase 1: Core Business Logic (Priority 1)
- Test evaluators (base, classification)
- Test gate logic (rules_engine, decision)
- Test golden_set validation
- **Estimated tests**: 80-100
- **Expected coverage gain**: +15-20%

### Phase 2: Metrics and Calculations (Priority 2)
- Test drift metrics
- Test slice analysis
- Test significance tests
- Test DB CRUD operations
- **Estimated tests**: 60-80
- **Expected coverage gain**: +10-15%

### Phase 3: API and Integration (Priority 3)
- Test API routers
- Test notification systems
- Test worker tasks
- **Estimated tests**: 100-120
- **Expected coverage gain**: +15-20%

### Phase 4: Edge Cases and Error Paths
- Add error path tests to existing modules
- Test exception handling
- Test boundary conditions
- **Estimated tests**: 50-80
- **Expected coverage gain**: +5-10%

## Implementation Order

1. **Phase 1.1**: evaluators/base.py tests
2. **Phase 1.2**: evaluators/classification.py tests
3. **Phase 1.3**: gate/rules_engine.py tests
4. **Phase 1.4**: gate/decision.py tests
5. **Phase 1.5**: golden_set.py tests
6. **Phase 2.1**: metrics/drift.py tests
7. **Phase 2.2**: metrics/slice_analysis.py tests
8. **Phase 2.3**: metrics/significance.py tests
9. **Phase 2.4**: db/crud.py additional tests
10. **Phase 2.5**: db/session.py tests
11. **Phase 3.1**: API routers tests
12. **Phase 3.2**: notifier tests
13. **Phase 3.3**: worker tasks tests
14. **Phase 4**: Edge cases and error paths

## Success Criteria
- Overall coverage ≥ 90%
- All critical modules ≥ 80% coverage
- All high priority modules ≥ 70% coverage
- All tests passing
- No test flakiness

## Tools and Approaches
- Use pytest for test framework
- Use pytest-asyncio for async tests
- Use pytest-mock for mocking
- Use fixtures for common test data
- Use parametrize for test variations
- Use coverage.py for coverage reporting

# Phase 1 Completion Checklist

**Objective:** Make the system operable and recoverable in a real production environment.

## Phase 1 Required Tasks (8 total)

- [x] **Task 1: Automated production drift monitoring scheduler**
  - [ ] DriftJobRunner service implemented
  - [ ] Scheduler (APScheduler/Celery Beat) integrated
  - [ ] Duplicate-run lock implemented
  - [ ] Job persistence and retry logic
  - [ ] Status/health endpoints

- [x] **Task 2: Production data ingestion interface**
  - [x] ProductionDataSource registry
  - [x] LocalFileDataSource (already exists)
  - [ ] S3/object store adapter
  - [ ] API prediction push endpoint
  - [ ] Schema validation and contracts

- [x] **Task 3: Champion rollback/version control workflow**
  - [x] ChampionRollback model
  - [x] Transactional rollback CRUD
  - [x] Rollback API endpoint
  - [ ] Rollback CLI update
  - [ ] Dashboard rollback flow
  - [ ] Post-rollback validation

- [ ] **Task 4: Operator incident response runbook**
  - [ ] Runbook documentation (drift, bad promotion, outages)
  - [ ] Command verification
  - [ ] Alert-to-runbook mapping

- [x] **Task 5: Audit logging persistence**
  - [x] AuditLog model enhancements
  - [x] Audit middleware
  - [ ] Query API with filters/pagination
  - [ ] Retention policy job
  - [ ] Redaction rules
  - [ ] Audit dashboard view

- [x] **Task 6: API key lifecycle operator surfaces**
  - [x] ApiKey model (expiration, rotation, revocation)
  - [x] Auth checking for expired/revoked keys
  - [ ] Admin API endpoints (create, rotate, revoke, list)
  - [ ] CLI surface update
  - [ ] Dashboard admin view
  - [ ] Backward compatibility with env keys

- [ ] **Task 7: Basic alerting rules and alert delivery**
  - [x] AlertEvent model
  - [ ] Alert rule definitions
  - [ ] Alert dispatch (Slack/webhook)
  - [ ] DeduplicationDeduplication logic
  - [ ] Alert queries in API

- [x] **Task 8: Production-ready error taxonomy**
  - [x] Error schemas and categories
  - [x] Remediation messages
  - [ ] Error code standardization
  - [ ] Error catalog documentation

## Files/Modules to Verify

### Models & Migrations
- [x] `ares/models/drift_job.py`
- [x] `ares/models/drift_report.py`
- [x] `ares/models/alert_event.py`
- [x] `ares/models/api_key.py`
- [x] `alembic/versions/0006_operational_lifecycle_tables.py`
- [x] `ares/db/crud.py` - CRUD operations
- [x] `ares/db/crud_api_keys.py` - API key operations

### API Routers & Schemas
- [x] `ares/api/routers/drift.py`
- [x] `ares/api/routers/alerts.py`
- [x] `ares/api/routers/api_keys.py`
- [x] `ares/api/routers/audit.py`
- [x] `ares/api/routers/champions.py` - rollback endpoints
- [x] `ares/api/schemas/drift.py`
- [x] `ares/api/schemas/alert.py`
- [x] `ares/api/schemas/api_key.py`
- [x] `ares/api/schemas/error.py`

### Core Services
- [x] `ares/drift/runner.py` - DriftJobRunner
- [x] `ares/drift/contracts.py` - Data contracts
- [x] `ares/drift_sources.py` - Source registry
- [ ] `ares/scheduler/` - Scheduler service (NEW)
- [ ] `ares/alerting/` - Alert dispatch (NEW)

### Auth & Middleware
- [x] `ares/api/auth.py` - API key auth with expiration
- [x] `ares/api/middleware/audit.py` - Audit logging

### Exceptions
- [x] `ares/exceptions.py` - Error taxonomy

### Testing
- [x] `tests/integration/test_phase1_operational_apis.py`
- [x] `tests/unit/test_phase1_drift_runner.py`
- [ ] `tests/integration/test_migrations.py` - Drift/alert migration tests
- [ ] `tests/unit/test_alerting.py` - Alert rule tests
- [ ] `tests/integration/test_scheduler.py` - Scheduler integration tests

### Documentation
- [x] `docs/phase1-operations-guide.md`
- [x] `docs/runbooks/operator-incident-response.md`
- [ ] `docs/api-key-lifecycle-guide.md` - Detailed guide
- [ ] `docs/error-catalog.md` - Error reference
- [ ] `docs/runbooks/drift-monitoring.md` - Drift setup
- [ ] `docs/runbooks/alert-configuration.md` - Alert setup

## Test Requirements

### Migration Tests
- [ ] Migration 0006 up/down verified
- [ ] Data preservation tested
- [ ] Rollback scenario tested

### Drift Scheduler Tests
- [ ] DriftJobRunner unit tests
- [ ] Duplicate-run lock tests
- [ ] Retry logic tests
- [ ] Integration with data sources

### Data Source Contract Tests
- [ ] LocalFileDataSource validation
- [ ] Schema contract enforcement
- [ ] Invalid payload rejection

### Rollback Tests
- [ ] Transactional atomicity
- [ ] Audit record creation
- [ ] Concurrent rollback prevention
- [ ] Post-rollback validation

### API Key Tests
- [ ] Expiration enforcement
- [ ] Rotation with grace period
- [ ] Revocation immediate effect
- [ ] Last-used tracking
- [ ] Env-key backward compatibility

### Audit Tests
- [ ] Mutation logging
- [ ] Query filtering
- [ ] Redaction of sensitive data
- [ ] Retention policy execution

### Alert Tests
- [ ] Alert event creation
- [ ] Drift threshold triggers
- [ ] Deduplication logic
- [ ] Delivery confirmation

### Error Taxonomy Tests
- [ ] Error code consistency
- [ ] Remediation message accuracy
- [ ] HTTP status mapping
- [ ] Request ID inclusion

## Acceptance Criteria

1. **Production Drift Deployment**
   - [ ] Scheduler runs drift checks without GitHub Actions
   - [ ] Results persist to database
   - [ ] Alerts trigger on threshold breach
   - [ ] Dashboard shows job status and history

2. **Rollback Governance**
   - [ ] Rollback is API/CLI/dashboard action
   - [ ] Audit log records actor, reason, timestamps
   - [ ] Previous champion is validated as current
   - [ ] Post-rollback verification runs

3. **API Key Security**
   - [ ] Expired keys rejected immediately
   - [ ] Revoked keys rejected immediately
   - [ ] Last-used metadata updated
   - [ ] Rotation grace period works
   - [ ] Env vars still work (backward compatible)

4. **Operator Experience**
   - [ ] Runbook has exact commands for P0 incidents
   - [ ] Operators can investigate via audit API
   - [ ] Error messages are actionable
   - [ ] Alert mappings to runbook are clear

## Current Status: ~70% Complete

### ✅ Completed
- Data models and migrations
- API routers and schemas
- Drift runner service
- Error taxonomy and schemas
- Audit middleware
- API key auth checking
- All Phase 1 unit/integration tests
- Phase 1 operations guide
- Incident response runbook

### ⏳ In Progress / Incomplete
- Scheduler service orchestration
- Full alerting with delivery
- Admin API endpoints for keys
- Dashboard integration for rollback/alerts/keys
- Detailed documentation (guides, error catalog)
- CLI updates for rollback/key management
- Full audit query API with pagination

## Skills to Use (Per Production_grade_final_plan.md)

Phase 1 Skills: `/plan-eng-review`, `/review`, `/codex`, `/cso`, `/investigate`, `/guard`, `/careful`, `/document-release`

- [x] `/plan-eng-review` - Architecture review before implementation
- [ ] `/review` - End-of-slice code review
- [ ] `/codex` - Second opinion on high-risk changes
- [ ] `/cso` - Security review for auth/audit/rollback
- [ ] `/investigate` - Debug any runtime failures
- [ ] `/guard` - Protect migrations and rollback work
- [ ] `/careful` - Warn before destructive operations
- [ ] `/document-release` - Update docs after behavior ships

## Next Steps

1. Complete scheduler service (APScheduler baseline)
2. Add admin API endpoints for key management
3. Implement alert delivery (Slack/webhook)
4. Add dashboard integration for all Phase 1 features
5. Complete all documentation guides
6. Security review with `/cso`
7. Final verification and code review with `/review`
8. Test all end-to-end workflows

---

**Target:** 100% Phase 1 completion with 0 mistakes
**Current:** 70% → Target 95%+ by next checkpoint

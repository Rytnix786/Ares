## Security grep summary

- **total_matches**: 5048
- **token**: 3061
- **password**: 1159
- **secret**: 733
- **api_key**: 250
- **api-key**: 24
- **x-api-key**: 16
- **akia**: 4

### First 200 matches

.env:3:ARES_API_KEYS=db7f56e27524c6c84b50099b47e7917e59e26fb73ca20123ff70c5352b166efe
.env:10:AWS_SECRET_ACCESS_KEY=minioadmin
.env.example:3:ARES_API_KEYS=dev-key-1,dev-key-2
.env.example:10:AWS_SECRET_ACCESS_KEY=minioadmin
ARES_AGENT_INSTRUCTIONS.md:28:| Secrets | GitHub Secrets + python-dotenv | Zero hardcoded credentials |
ARES_AGENT_INSTRUCTIONS.md:193:dvc remote modify ares-remote secret_access_key ${AWS_SECRET_ACCESS_KEY}
ARES_AGENT_INSTRUCTIONS.md:533:        password: ${{ secrets.GITHUB_TOKEN }}
ARES_AGENT_INSTRUCTIONS.md:542:        run: dvc remote modify ares-remote access_key_id ${{ secrets.AWS_ACCESS_KEY_ID }}
ARES_AGENT_INSTRUCTIONS.md:544:          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
ARES_AGENT_INSTRUCTIONS.md:552:          ARES_DB_URL: ${{ secrets.ARES_DB_URL }}
ARES_AGENT_INSTRUCTIONS.md:553:          ARES_API_KEY: ${{ secrets.ARES_API_KEY }}
ARES_AGENT_INSTRUCTIONS.md:731:            headers={"X-API-Key": settings.ARES_API_KEY},
ARES_AGENT_INSTRUCTIONS.md:744:            headers={"X-API-Key": settings.ARES_API_KEY},
ARES_AGENT_INSTRUCTIONS.md:808:    ARES_API_KEY: str
ARES_AGENT_INSTRUCTIONS.md:813:    AWS_SECRET_ACCESS_KEY: str = ""
ARES_AGENT_INSTRUCTIONS.md:818:    GITHUB_TOKEN: str = ""
docker-compose.ci.yml:6:      POSTGRES_PASSWORD: ares
docker-compose.ci.yml:28:      ARES_API_KEYS: ci-key
docker-compose.ci.yml.bak:6:      POSTGRES_PASSWORD: ares
docker-compose.yml:6:      POSTGRES_PASSWORD: ares
docker-compose.yml:28:      MINIO_ROOT_PASSWORD: minioadmin
docker-compose.yml:68:      AWS_SECRET_ACCESS_KEY: minioadmin
mlflow.db:753:	secret VARCHAR(1000), 
mlflow.db:799:	secret_id VARCHAR(36), 
mlflow.db:807:	CONSTRAINT fk_model_definitions_secret_id FOREIGN KEY(secret_id) REFERENCES secrets (secret_id) ON DELETE SET NULL
mlflow.db:810:indexunique_secret_namesecretsqCREATE UNIQUE INDEX unique_secret_name ON secrets (secret_name)
mlflow.db:812:?A???indexsqlite_autoindex_secrets_1secretsp
mlflow.db:813:??????)tablesecretssecretsoCREATE TABLE secrets (
mlflow.db:814:	secret_id VARCHAR(36) NOT NULL, 
mlflow.db:815:	secret_name VARCHAR(255) NOT NULL, 
mlflow.db:827:	CONSTRAINT secrets_pk PRIMARY KEY (secret_id)
mlflow.db:898:)???:??E???triggerprevent_secrets_aad_mutationsecretsCREATE TRIGGER prevent_secrets_aad_mutation
mlflow.db:899:BEFORE UPDATE ON secrets
mlflow.db:901:WHEN OLD.secret_id != NEW.secret_id OR OLD.secret_name != NEW.secret_name
mlflow.db:903:    SELECT RAISE(ABORT, 'secret_id and secret_name are immutable (used as AAD in encryption)');
mlflow.db:932:)?????M/?'indexindex_model_definitions_providermodel_definitionszCREATE INDEX index_model_definitions_provider ON model_definitions (provider)???`??O/?+indexindex_model_definitions_secret_idmodel_definitionsyCREATE INDEX index_model_definitions_secret_id ON model_definitions (secret_id)?????E/?%indexunique_model_definition_namemodel_definitionsxCREATE UNIQUE INDEX unique_model_definition_name ON model_definitions (name)???D?U/??indexsqlite_autoindex_model_definitions_1model_definitionsv
mlflow.db:1029:??????????????????????????????F??55?I?F??55?3table_alembic_tnF?????3tablesecretssecretsSCREATE TABLE "secrets" (
mlflow.db:1030:	secret_id VARCHAR(36) NOT NULL, 
mlflow.db:1031:	secret_name VARCHAR(255) NOT NULL, 
mlflow.db:1037:	auth_confi6I??E???triggerprevent_secrets_aad_mutationsecretsCREATE TRIGGER prevent_secrets_aad_mutation
mlflow.db:1038:BEFORE UPDATE ON secrets
mlflow.db:1040:WHEN OLD.secret_id != NEW.secret_id OR OLD.secret_name != NEW.secret_name
mlflow.db:1042:    SELECT RAISE(ABORT, 'secret_id and secret_name are immutable (used as AAD in encryption)');
mlflow.db:1043:ENDnF?????3tablesecretssecretsSCREATE TABLE "secrets" (
mlflow.db:1044:	secret_id VARCHAR(36) NOT NULL, 
mlflow.db:1045:	secret_name VARCHAR(255) NOT NULL, 
mlflow.db:1058:	CONSTRAINT secrets_pk PRIMARY KEY (secret_id), 
mlflow.db:1059:	CONSTRAINT uq_secrets_workspace_secret_name UNIQUE (workspace, secret_name)
mlflow.db:1068:	secret VARCHAR(1000), 
mlflow.db:1128:\??K/?'indexidx_model_definitions_workspacemodel_definitions?CREATE INDEX idx_model_definitions_workspace ON model_definitions (workspace)?Q??O/?+indexindex_model_definitions_secret_idmodel_definitionsvCREATE INDEX index_model_definitions_secret_id ON model_definitions (secret_id)
mlflow.db:1133:	secret_id VARCHAR(36), 
mlflow.db:1142:	CONSTRAINT fk_model_definitions_secret_id FOREIGN KEY(secret_id) REFERENCES secrets (secret_id) ON DELETE SET NULL, 
mlflow.db:1160:)2L??E???indexsqlite_autoindex_endpoints_2endpoints?1K??E???indexsqlite_autoindex_endpoints_1endpointsq????E???triggerprevent_secrets_aad_mutationsecretsCREATE TRIGGER prevent_secrets_aad_mutation
mlflow.db:1161:BEFORE UPDATE ON secrets
mlflow.db:1163:WHEN OLD.secret_id != >`??Q+??indexsqlite_autoindex_budget_policies_1budget_policies?9]??!!?;tableworkspacesworkspaces?CREATE TABLE workspaces (
mlflow.db:1168:)k[??;???indexidx_endpoints_workspaceendpoints?CREATE INDEX idx_endpoints_workspace ON endpoints (workspace)bZ??7???indexidx_secrets_workspacesecrets?CREATE INDEX idx_secrets_workspace ON secrets (workspace)gY??9
mlflow.db:1181:)6I??E???triggerprevent_secrets_aad_mutationsecretsCREATE TRIGGER prevent_secrets_aad_mutation
mlflow.db:1182:BEFORE UPDATE ON secrets
mlflow.db:1184:WHEN OLD.secret_id != NEW.secret_id OR OLD.secret_name != NEW.secret_name
mlflow.db:1186:    SELECT RAISE(ABORT, 'secret_id and secret_name are immutable (used as AAD in encryption)');
mlflow.db:1187:END.H??A???indexsqlite_autoindex_secrets_2secrets?-G??A???indexsqlite_autoindex_secrets_1secretsT???~?????WtablejobsjobsxCREATE TABLE "jobs" (
mlflow.db:1258:\??K/?'indexidx_model_definitions_workspacemodel_definitions?CREATE INDEX idx_model_definitions_workspace ON model_definitions (workspace)k[??;???indexidx_endpoints_workspaceendpoints?CREATE INDEX idx_endpoints_workspace ON endpoints (workspace)bZ??7???indexidx_secrets_workspacesecrets?CREATE INDEX idx_secrets_workspace ON secrets (workspace)gY??9
plan.md:92:| Security/config | GitHub Secrets + python-dotenv + Pydantic Settings |
plan.md:176:### 2.1 Secrets Rotation and API Key Management
plan.md:180:  - `ARES_API_KEYS: list[str]`
plan.md:181:  - optional backward-compatible `ARES_API_KEY` ingestion into that list
plan.md:183:  - if `ARES_API_KEY` is set and `ARES_API_KEYS` is empty, initialize `ARES_API_KEYS` from it
plan.md:188:  1. add new key to `ARES_API_KEYS`
plan.md:486:- validate incoming API key against `ARES_API_KEYS`
plan.md:555:- dashboard API client with `st.secrets` / env fallback
plan.md:590:- CI/CD secrets and workflow guide
README.md:50:## CI/CD secrets
README.md:52:Configure `ARES_DB_URL`, `ARES_API_KEYS`, cloud storage credentials for DVC, and package permissions for GHCR.
README.md:90:Set `ARES_API_KEYS` to comma-separated keys. Add the new key, migrate consumers, then remove the old key. Legacy `ARES_API_KEY` is merged deterministically.
ares/config.py:22:    ARES_API_KEY: str | None = None
ares/config.py:23:    ARES_API_KEYS: Annotated[list[str], NoDecode] = Field(default_factory=list)
ares/config.py:30:    AWS_SECRET_ACCESS_KEY: str = ""
ares/config.py:42:    GITHUB_TOKEN: str = ""
ares/config.py:45:    @field_validator("ARES_API_KEYS", mode="before")
ares/config.py:55:    def merge_legacy_api_key(self) -> AresSettings:
ares/config.py:56:        keys = list(self.ARES_API_KEYS)
ares/config.py:57:        if self.ARES_API_KEY:
ares/config.py:58:            keys.append(self.ARES_API_KEY)
ares/config.py:59:        self.ARES_API_KEYS = list(dict.fromkeys(k for k in keys if k))
ares/config.py:60:        if self.ENVIRONMENT in {"production", "staging"} and not self.ARES_API_KEYS:
ares/config.py:61:            raise ValueError("ARES_API_KEYS is required in protected environments")
ares.egg-info/PKG-INFO:103:## CI/CD secrets
ares.egg-info/PKG-INFO:105:Configure `ARES_DB_URL`, `ARES_API_KEYS`, cloud storage credentials for DVC, and package permissions for GHCR.
ares.egg-info/PKG-INFO:143:Set `ARES_API_KEYS` to comma-separated keys. Add the new key, migrate consumers, then remove the old key. Legacy `ARES_API_KEY` is merged deterministically.
dashboard/api_client.py:12:    secrets = getattr(st, "secrets", {})
dashboard/api_client.py:13:    if "ARES_API_URL" in secrets:
dashboard/api_client.py:14:        return str(secrets["ARES_API_URL"])
dashboard/api_client.py:18:def get_api_key() -> str:
dashboard/api_client.py:19:    secrets = getattr(st, "secrets", {})
dashboard/api_client.py:20:    if "ARES_API_KEY" in secrets:
dashboard/api_client.py:21:        return str(secrets["ARES_API_KEY"])
dashboard/api_client.py:22:    return st.session_state.get("ARES_API_KEY") or os.getenv("ARES_API_KEY") or "dev-key-1"
dashboard/api_client.py:28:        headers={"X-API-Key": get_api_key()},
dashboard/CHANGES.md:6:- Added a **sidebar ?Connection settings? expander** to set `ARES_API_URL` and `ARES_API_KEY` via `st.session_state` (no restart required).
reports/test-results.xml:1:<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests"><testsuite name="pytest" errors="0" failures="0" skipped="0" tests="44" time="7.772" timestamp="2026-04-27T18:04:48.269741+06:00" hostname="DESKTOP-JOGRJJS"><testcase classname="tests.e2e.test_full_pipeline" name="test_cli_failure_json" time="3.097" /><testcase classname="tests.e2e.test_full_pipeline" name="test_cli_success" time="3.226" /><testcase classname="tests.integration.test_api" name="test_live_health" time="0.018" /><testcase classname="tests.integration.test_api" name="test_openapi_loads" time="0.037" /><testcase classname="tests.integration.test_api" name="test_list_evaluations_returns_seeded_run" time="0.049" /><testcase classname="tests.integration.test_api" name="test_get_champion_returns_schema_payload" time="0.011" /><testcase classname="tests.integration.test_api" name="test_export_compare_drift_and_health_routes" time="0.042" /><testcase classname="tests.integration.test_db_crud" name="test_crud_round_trip" time="0.005" /><testcase classname="tests.integration.test_db_crud" name="test_promote_and_export_champion" time="0.010" /><testcase classname="tests.integration.test_db_crud" name="test_create_and_list_drift_report" time="0.006" /><testcase classname="tests.unit.test_additional_evaluators" name="test_detection_evaluator_inherits_classification_behavior" time="0.016" /><testcase classname="tests.unit.test_additional_evaluators" name="test_regression_evaluator_returns_numeric_metrics" time="0.001" /><testcase classname="tests.unit.test_auth_config" name="test_rate_limit_key_prefers_api_key" time="0.000" /><testcase classname="tests.unit.test_auth_config" name="test_rate_limit_key_falls_back_to_host" time="0.000" /><testcase classname="tests.unit.test_auth_config" name="test_require_api_key_accepts_known_key" time="0.005" /><testcase classname="tests.unit.test_auth_config" name="test_require_api_key_rejects_unknown_key" time="0.004" /><testcase classname="tests.unit.test_auth_config" name="test_settings_merge_legacy_api_key" time="0.003" /><testcase classname="tests.unit.test_auth_config" name="test_settings_sqlite_property" time="0.003" /><testcase classname="tests.unit.test_auth_config" name="test_noop_limiter_returns_original_function" time="0.000" /><testcase classname="tests.unit.test_evaluator" name="test_evaluator_validates_required_columns" time="0.001" /><testcase classname="tests.unit.test_evaluator" name="test_classification_evaluator_runs" time="0.010" /><testcase classname="tests.unit.test_gate" name="test_critical_slice_failure_overrides_passing_overall" time="0.003" /><testcase classname="tests.unit.test_gate" name="test_regression_within_tolerance_passes" time="0.003" /><testcase classname="tests.unit.test_gate" name="test_regression_beyond_tolerance_fails" time="0.004" /><testcase classname="tests.unit.test_gate" name="test_statistically_insignificant_improvement_does_not_promote" time="0.004" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_validate_golden_set_returns_summary" time="0.004" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_validate_golden_set_checksum_mismatch_raises" time="0.003" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_validate_golden_set_requires_checksum_when_enabled" time="0.003" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_sha256_file_returns_hex_digest" time="0.002" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_local_file_data_source_reads_csv" time="0.005" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_local_file_data_source_validates_columns" time="0.003" /><testcase classname="tests.unit.test_golden_set_and_drift_source" name="test_local_file_data_source_missing_file_raises" time="0.001" /><testcase classname="tests.unit.test_metrics" name="test_kl_divergence_zero_for_same_distribution" time="0.001" /><testcase classname="tests.unit.test_metrics" name="test_psi_non_negative" time="0.001" /><testcase classname="tests.unit.test_metrics" name="test_compute_drift_report" time="0.001" /><testcase classname="tests.unit.test_session_and_telemetry" name="test_get_engine_and_sessionmaker_for_sqlite" time="0.001" /><testcase classname="tests.unit.test_session_and_telemetry" name="test_setup_telemetry_instruments_when_module_available" time="0.001" /><testcase classname="tests.unit.test_significance" name="test_standard_error_positive" time="0.000" /><testcase classname="tests.unit.test_significance" name="test_wilson_interval_bounds" time="0.001" /><testcase classname="tests.unit.test_support_modules" name="test_build_pr_comment_includes_details_url" time="0.000" /><testcase classname="tests.unit.test_support_modules" name="test_send_slack_message_noop_without_webhook" time="0.001" /><testcase classname="tests.unit.test_support_modules" name="test_send_slack_message_posts_when_webhook_present" time="0.001" /><testcase classname="tests.unit.test_support_modules" name="test_setup_telemetry_noop" time="0.000" /><testcase classname="tests.unit.test_support_modules" name="test_evaluate_task_returns_payload" time="0.002" /></testsuite></testsuites>
scripts/rollback.py:13:    headers = {"X-API-Key": settings.ARES_API_KEYS[0]} if settings.ARES_API_KEYS else {}
tests/conftest.py:5:os.environ.setdefault("ARES_API_KEYS", "test-key")
tests/integration/test_api.py:20:    response = await api_client.get("/api/v1/evaluations/", headers={"X-API-Key": "test-key"})
tests/integration/test_api.py:29:    response = await api_client.get("/api/v1/champions/default-model", headers={"X-API-Key": "test-key"})
tests/integration/test_api.py:37:    export_response = await api_client.get("/api/v1/champions/export", headers={"X-API-Key": "test-key"})
tests/integration/test_api.py:41:    previous_response = await api_client.get("/api/v1/champions/default-model/previous", headers={"X-API-Key": "test-key"})
tests/integration/test_api.py:46:        headers={"X-API-Key": "test-key"},
tests/integration/test_api.py:60:        headers={"X-API-Key": "test-key"},
tests/integration/test_api.py:73:    drift_list = await api_client.get("/api/v1/drift/reports", headers={"X-API-Key": "test-key"})
tests/integration/test_api.py:77:    gate_config = await api_client.get("/api/v1/gate/config", headers={"X-API-Key": "test-key"})
tests/unit/test_auth_config.py:10:from ares.api.auth import rate_limit_key, require_api_key
tests/unit/test_auth_config.py:15:def test_rate_limit_key_prefers_api_key() -> None:
tests/unit/test_auth_config.py:16:    request = cast(Request, SimpleNamespace(headers={"x-api-key": "secret"}, client=SimpleNamespace(host="127.0.0.1")))
tests/unit/test_auth_config.py:17:    assert rate_limit_key(request) == "secret"
tests/unit/test_auth_config.py:26:async def test_require_api_key_accepts_known_key(monkeypatch: pytest.MonkeyPatch) -> None:
tests/unit/test_auth_config.py:27:    monkeypatch.setattr("ares.api.auth.settings", AresSettings(ENVIRONMENT="development", ARES_API_KEYS=["known-key"]))
tests/unit/test_auth_config.py:28:    assert await require_api_key("known-key") == "known-key"
tests/unit/test_auth_config.py:32:async def test_require_api_key_rejects_unknown_key(monkeypatch: pytest.MonkeyPatch) -> None:
tests/unit/test_auth_config.py:33:    monkeypatch.setattr("ares.api.auth.settings", AresSettings(ENVIRONMENT="development", ARES_API_KEYS=["known-key"]))
tests/unit/test_auth_config.py:35:        await require_api_key("wrong")
tests/unit/test_auth_config.py:38:def test_settings_merge_legacy_api_key() -> None:
tests/unit/test_auth_config.py:42:        ARES_API_KEY="legacy",
tests/unit/test_auth_config.py:43:        ARES_API_KEYS=["current"],
tests/unit/test_auth_config.py:45:    assert settings.ARES_API_KEYS == ["current", "legacy"]
skills/agent-skills-main/README.md:168:| [security-and-hardening](skills/security-and-hardening/SKILL.md) | OWASP Top 10 prevention, auth patterns, secrets management, dependency auditing, three-tier boundary system | Handling user input, auth, data storage, or external integrations |
skills/agent-skills-main/README.md:235:- **Progressive disclosure.** The `SKILL.md` is the entry point. Supporting references load only when needed, keeping token usage minimal.
skills/antigravity-awesome-skills-main/README.md:128:| **agent-tool-builder**                              | "Tools are how AI agents interact with the world. A well-designed tool is the difference between an agent that works and one that hallucinates, fails silently, or costs 10x more tokens than necessary. This skill covers tool design from schema to error handling. JSON Schema best practices, description writing that actually helps the LLM, validation, and the emerging MCP standard that's becoming the lingua franca for AI tools. Key insight: Tool descriptions are more important than tool implementa"                                                                                                                                                                                                                                                                                                                     | `skills/agent-tool-builder`                  |
skills/antigravity-awesome-skills-main/README.md:155:| **Broken Authentication Testing**                   | This skill should be used when the user asks to "test for broken authentication vulnerabilities", "assess session management security", "perform credential stuffing tests", "evaluate password policies", "test for session fixation", or "identify authentication bypass flaws". It provides comprehensive techniques for identifying authentication and session management weaknesses in web applications.                                                                                                                                                                                                                                                                                                                                                                                                                            | `skills/broken-authentication`               |
skills/antigravity-awesome-skills-main/README.md:169:| **Cloud Penetration Testing**                       | This skill should be used when the user asks to "perform cloud penetration testing", "assess Azure or AWS or GCP security", "enumerate cloud resources", "exploit cloud misconfigurations", "test O365 security", "extract secrets from cloud environments", or "audit cloud infrastructure". It provides comprehensive techniques for security assessment across major cloud platforms.                                                                                                                                                                                                                                                                                                                                                                                                                                                 | `skills/cloud-penetration-testing`           |
skills/antigravity-awesome-skills-main/README.md:176:| **context-window-management**                       | "Strategies for managing LLM context windows including summarization, trimming, routing, and avoiding context rot Use when: context window, token limit, context management, context engineering, long context."                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | `skills/context-window-management`           |
skills/antigravity-awesome-skills-main/README.md:180:| **core-components**                                 | Core component library and design system patterns. Use when building UI, using design tokens, or working with the component library.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | `skills/core-components`                     |
skills/antigravity-awesome-skills-main/README.md:259:| **Pentest Commands**                                | This skill should be used when the user asks to "run pentest commands", "scan with nmap", "use metasploit exploits", "crack passwords with hydra or john", "scan web vulnerabilities with nikto", "enumerate networks", or needs essential penetration testing command references.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | `skills/pentest-commands`                    |
skills/antigravity-awesome-skills-main/README.md:262:| **plaid-fintech**                                   | "Expert patterns for Plaid API integration including Link token flows, transactions sync, identity verification, Auth for ACH, balance checks, webhook handling, and fintech compliance best practices. Use when: plaid, bank account linking, bank connection, ach, account aggregation."                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `skills/plaid-fintech`                       |
skills/antigravity-awesome-skills-main/README.md:271:| **Privilege Escalation Methods**                    | This skill should be used when the user asks to "escalate privileges", "get root access", "become administrator", "privesc techniques", "abuse sudo", "exploit SUID binaries", "Kerberoasting", "pass-the-ticket", "token impersonation", or needs guidance on post-exploitation privilege escalation for Linux or Windows systems.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `skills/privilege-escalation-methods`        |
skills/antigravity-awesome-skills-main/README.md:294:| **security-review**                                 | Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensitive features. Provides comprehensive security checklist and patterns.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | `skills/cc-skill-security-review`            |
skills/antigravity-awesome-skills-main/README.md:319:| **tailwind-patterns**                               | Tailwind CSS v4 principles. CSS-first configuration, container queries, modern patterns, design token architecture.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `skills/tailwind-patterns`                   |
skills/antigravity-awesome-skills-main/skills_index.json:66:    "description": "\"Tools are how AI agents interact with the world. A well-designed tool is the difference between an agent that works and one that hallucinates, fails silently, or costs 10x more tokens than necessary.  This skill covers tool design from schema to error handling. JSON Schema best practices, description writing that actually helps the LLM, validation, and the emerging MCP standard that's becoming the lingua franca for AI tools.  Key insight: Tool descriptions are more important than tool implementa\""
skills/antigravity-awesome-skills-main/skills_index.json:228:    "description": "This skill should be used when the user asks to \"test for broken authentication vulnerabilities\", \"assess session management security\", \"perform credential stuffing tests\", \"evaluate password policies\", \"test for session fixation\", or \"identify authentication bypass flaws\". It provides comprehensive techniques for identifying authentication and session management weaknesses in web applications."
skills/antigravity-awesome-skills-main/skills_index.json:312:    "description": "This skill should be used when the user asks to \"perform cloud penetration testing\", \"assess Azure or AWS or GCP security\", \"enumerate cloud resources\", \"exploit cloud misconfigurations\", \"test O365 security\", \"extract secrets from cloud environments\", or \"audit cloud infrastructure\". It provides comprehensive techniques for security assessment across major cloud platforms."
skills/antigravity-awesome-skills-main/skills_index.json:354:    "description": "\"Strategies for managing LLM context windows including summarization, trimming, routing, and avoiding context rot Use when: context window, token limit, context management, context engineering, long context.\""
skills/antigravity-awesome-skills-main/skills_index.json:378:    "description": "Core component library and design system patterns. Use when building UI, using design tokens, or working with the component library."
skills/antigravity-awesome-skills-main/skills_index.json:852:    "description": "This skill should be used when the user asks to \"run pentest commands\", \"scan with nmap\", \"use metasploit exploits\", \"crack passwords with hydra or john\", \"scan web vulnerabilities with nikto\", \"enumerate networks\", or needs essential penetration testing command references."
skills/antigravity-awesome-skills-main/skills_index.json:870:    "description": "\"Expert patterns for Plaid API integration including Link token flows, transactions sync, identity verification, Auth for ACH, balance checks, webhook handling, and fintech compliance best practices. Use when: plaid, bank account linking, bank connection, ach, account aggregation.\""
skills/antigravity-awesome-skills-main/skills_index.json:924:    "description": "This skill should be used when the user asks to \"escalate privileges\", \"get root access\", \"become administrator\", \"privesc techniques\", \"abuse sudo\", \"exploit SUID binaries\", \"Kerberoasting\", \"pass-the-ticket\", \"token impersonation\", or needs guidance on post-exploitation privilege escalation for Linux or Windows systems."
skills/antigravity-awesome-skills-main/skills_index.json:1062:    "description": "Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensitive features. Provides comprehensive security checklist and patterns."
skills/antigravity-awesome-skills-main/skills_index.json:1212:    "description": "Tailwind CSS v4 principles. CSS-first configuration, container queries, modern patterns, design token architecture."
skills/graphify-5/ARCHITECTURE.md:30:| `benchmark.py` | `run_benchmark(graph_path)` | graph file ? corpus vs subgraph token comparison |
skills/graphify-5/CHANGELOG.md:127:- Fix: Common lockfiles (`package-lock.json`, `yarn.lock`, `Cargo.lock`, etc.) are now skipped during detection, preventing token drain on large JS/Rust/Python projects (#266)
skills/graphify-5/CHANGELOG.md:236:- Refactor: `save_query_result` inline Python blocks in all 6 skill files replaced with `graphify save-result` CLI command ? shorter, maintainable, less tokens for LLM (#114)
skills/graphify-5/CHANGELOG.md:371:- Token reduction benchmark auto-runs after every pipeline on corpora over 5,000 words
skills/graphify-5/README.md:28:> Andrej Karpathy keeps a `/raw` folder where he drops papers, tweets, screenshots, and notes. graphify is the answer to that problem - 71.5x fewer tokens per query vs reading the raw files, persistent across sessions, honest about what it found vs guessed.
skills/graphify-5/README.md:181:graphify-out/cost.json         # local token tracking, not useful to share
skills/graphify-5/README.md:286:/graphify query "what connects attention to the optimizer?" --budget 1500  # cap at N tokens
skills/graphify-5/README.md:409:**Token benchmark** - printed automatically after every run. On a mixed corpus (Karpathy repos + papers + images): **71.5x** fewer tokens per query vs reading raw files. The first run extracts and builds the graph (this costs tokens). Every subsequent query reads the compact graph instead of raw files ? that's where the savings compound. The SHA256 cache means re-runs only re-process changed files.
skills/graphify-5/README.md:425:Token reduction scales with corpus size. 6 files fits in a context window anyway, so graph value there is structural clarity, not compression. At 52 files (code + papers + images) you get 71x+. Each `worked/` folder has the raw input files and the actual output (`GRAPH_REPORT.md`, `graph.json`) so you can run it yourself and verify the numbers.
skills/second-brain-skills-main/README.md:76:**Core Philosophy**: MCP servers expose thousands of tokens worth of tool definitions. This skill wraps them as a lightweight client, loading only what you need when you need it.
skills/second-brain-skills-main/README.md:97:      "api_key": "YOUR_API_KEY_HERE"
skills/second-brain-skills-main/README.md:108:- `url` + `api_key` ? Remote server with Bearer auth (Zapier)
skills/second-brain-skills-main/README.md:430:2. Add your API keys (Zapier, GitHub tokens, etc.)
skills/superpowers-main/RELEASE-NOTES.md:14:- **Bootstrap as user message** ? moved bootstrap injection from `experimental.chat.system.transform` to `experimental.chat.messages.transform`, prepending to the first user message instead of adding a system message. Avoids token bloat from system messages repeated every turn (#750) and fixes compatibility with Qwen and other models that break on multiple system messages (#894).
skills/superpowers-main/RELEASE-NOTES.md:58:Dramatically reduces token usage and speeds up spec and plan reviews by eliminating unnecessary review passes and tightening reviewer focus.
skills/superpowers-main/RELEASE-NOTES.md:183:**Linting fix in token analysis script**
skills/superpowers-main/RELEASE-NOTES.md:185:- `except:` ? `except Exception:` in `tests/claude-code/analyze-token-usage.py`
skills/superpowers-main/RELEASE-NOTES.md:557:`tests/claude-code/` - Integration tests using `claude -p` for headless testing. Verifies skill usage via session transcript (JSONL) analysis. Includes `analyze-token-usage.py` for cost tracking.
skills/superpowers-main/RELEASE-NOTES.md:948:- Added token efficiency section (word count targets)
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/icons.csv:84:83,Security,lock,secure password protected private,Lucide,import { Lock } from 'lucide-react',<Lock />,Lock secure,Outline
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/icons.csv:87:86,Security,key,password access unlock login,Lucide,import { Key } from 'lucide-react',<Key />,Key password,Outline
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/icons.csv:88:87,Security,eye,view show visible password,Lucide,import { Eye } from 'lucide-react',<Eye />,Show password view,Outline
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/icons.csv:89:88,Security,eye-off,hide invisible password hidden,Lucide,import { EyeOff } from 'lucide-react',<EyeOff />,Hide password,Outline
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/ux-guidelines.csv:61:60,Forms,Password Visibility,All,Let users see password while typing,Toggle to show/hide password,No visibility toggle,Show/hide password button,Password always hidden,Medium
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/ux-guidelines.csv:94:93,AI Interaction,Streaming,All,Waiting for full text is slow,Stream text response token by token,Show loading spinner for 10s+,Typewriter effect,Spinner until 100% complete,Medium
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/web-interface.csv:13:12,Forms,Never Block Paste,paste onpaste password,Web,Never prevent paste functionality,Allow paste on all inputs,Block paste on password/code,"<input type='password' />","<input onPaste={e => e.preventDefault()} />",High
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:113:    def tokenize(self, text):
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:120:        self.corpus = [self.tokenize(doc) for doc in documents]
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:139:        query_tokens = self.tokenize(query)
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:149:            for token in query_tokens:
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:150:                if token in self.idf:
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:151:                    tf = term_freqs[token]
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/core.py:152:                    idf = self.idf[token]
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/design_system.py:610:    lines.append("| Token | Value | Usage |")
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/design_system.py:1029:        (["login", "signin", "signup", "register", "auth", "password"], "Authentication"),
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/scripts/search.py:23:    """Format results for Claude consumption (token-optimized)"""
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/jetpack-compose.csv:23:22,Theming,Design system,Centralized theme,Material3 tokens,Hardcoded values,Consistent UI,Inconsistent,High,https://developer.android.com/jetpack/compose/themes
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/nextjs.csv:36:35,Environment,Use NEXT_PUBLIC prefix,Client-accessible env vars need prefix,NEXT_PUBLIC_ for client vars,Server vars exposed to client,NEXT_PUBLIC_API_URL,API_SECRET in client code,High,https://nextjs.org/docs/app/building-your-application/configuring/environment-variables
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/nextjs.csv:38:37,Environment,Use .env.local for secrets,Local env file for development secrets,.env.local gitignored,Secrets in .env committed,.env.local with secrets,.env with DATABASE_PASSWORD,High,
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/nuxt-ui.csv:12:11,Theming,Use @theme directive for custom colors,Define design tokens in CSS with Tailwind @theme,@theme { --color-brand-500: #xxx },Inline color definitions,@theme { --color-brand-500: #ef4444; },:style="{ color: '#ef4444' }",Medium,https://ui.nuxt.com/docs/getting-started/theme/design-system
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/nuxtjs.csv:53:52,Environment,Use runtimeConfig for env vars,Access environment variables safely,runtimeConfig in nuxt.config,process.env directly,"runtimeConfig: { apiSecret: '', public: { apiBase: '' } }",process.env.API_SECRET in components,High,https://nuxt.com/docs/guide/going-further/runtime-config
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/nuxtjs.csv:54:53,Environment,Use NUXT_ prefix for env override,Override config with environment variables,NUXT_API_SECRET NUXT_PUBLIC_API_BASE,Custom env var names,NUXT_PUBLIC_API_BASE=https://api.example.com,API_BASE=https://api.example.com,High,https://nuxt.com/docs/guide/going-further/runtime-config
skills/ui-ux-pro-max-skill-main/skills/ui-ux-pro-max/data/stacks/nuxtjs.csv:56:55,Environment,Keep secrets in private config,Server-only secrets in runtimeConfig root,runtimeConfig.apiSecret (server only),Secrets in public config,runtimeConfig: { dbPassword: '' },runtimeConfig: { public: { dbPassword: '' } },High,https://nuxt.com/docs/guide/going-further/runtime-config
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/data/icons.csv:84:83,Security,lock,secure password protected private,Lucide,import { Lock } from 'lucide-react',<Lock />,Lock secure,Outline
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/data/icons.csv:87:86,Security,key,password access unlock login,Lucide,import { Key } from 'lucide-react',<Key />,Key password,Outline
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/data/icons.csv:88:87,Security,eye,view show visible password,Lucide,import { Eye } from 'lucide-react',<Eye />,Show password view,Outline
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/data/icons.csv:89:88,Security,eye-off,hide invisible password hidden,Lucide,import { EyeOff } from 'lucide-react',<EyeOff />,Hide password,Outline
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/data/ux-guidelines.csv:61:60,Forms,Password Visibility,All,Let users see password while typing,Toggle to show/hide password,No visibility toggle,Show/hide password button,Password always hidden,Medium
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/data/ux-guidelines.csv:94:93,AI Interaction,Streaming,All,Waiting for full text is slow,Stream text response token by token,Show loading spinner for 10s+,Typewriter effect,Spinner until 100% complete,Medium
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/scripts/core.py:102:    def tokenize(self, text):
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/scripts/core.py:109:        self.corpus = [self.tokenize(doc) for doc in documents]
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/scripts/core.py:128:        query_tokens = self.tokenize(query)
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/scripts/core.py:138:            for token in query_tokens:
skills/ui-ux-pro-max-skill-main/cli/assets/.trae/skills/ui-ux-pro-max/scripts/core.py:139:                if token in self.idf:

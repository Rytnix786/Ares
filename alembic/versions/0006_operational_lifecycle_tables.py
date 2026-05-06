from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_operational_lifecycle_tables"
down_revision = "0005_add_webhooks_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drift_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("job_name", sa.String(length=256), nullable=False),
        sa.Column("schedule", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_config", sa.JSON(), nullable=False),
        sa.Column("reference_config", sa.JSON(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_name", "job_name", name="uq_drift_jobs_model_name_job_name"),
    )
    op.create_index(op.f("ix_drift_jobs_model_name"), "drift_jobs", ["model_name"], unique=False)
    op.create_index("ix_drift_jobs_status_next_run_at", "drift_jobs", ["status", "next_run_at"], unique=False)

    op.create_table(
        "drift_job_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("features_evaluated", sa.Integer(), nullable=False),
        sa.Column("alerts_triggered", sa.Integer(), nullable=False),
        sa.Column("max_severity", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("run_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["drift_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drift_job_runs_job_id"), "drift_job_runs", ["job_id"], unique=False)
    op.create_index(op.f("ix_drift_job_runs_model_name"), "drift_job_runs", ["model_name"], unique=False)
    op.create_index("ix_drift_job_runs_model_name_created_at", "drift_job_runs", ["model_name", "created_at"], unique=False)
    op.create_index("ix_drift_job_runs_status_created_at", "drift_job_runs", ["status", "created_at"], unique=False)

    with op.batch_alter_table("drift_reports") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("run_id", sa.String(), nullable=True))
        batch_op.create_foreign_key("fk_drift_reports_job_id_drift_jobs", "drift_jobs", ["job_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_drift_reports_run_id_drift_job_runs", "drift_job_runs", ["run_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_drift_reports_job_id", ["job_id"])
        batch_op.create_index("ix_drift_reports_run_id", ["run_id"])
        batch_op.create_index("ix_drift_reports_model_name_created_at", ["model_name", "created_at"])
        batch_op.create_index("ix_drift_reports_is_alerting_created_at", ["is_alerting", "created_at"])

    with op.batch_alter_table("model_champions") as batch_op:
        batch_op.add_column(sa.Column("previous_champion_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("action", sa.String(length=32), nullable=False, server_default="promotion"))
        batch_op.add_column(sa.Column("rolled_back_from_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("rollback_reason", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("rollback_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("lifecycle_metadata", sa.JSON(), nullable=True))
        batch_op.create_foreign_key("fk_model_champions_previous_champion_id", "model_champions", ["previous_champion_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_model_champions_rolled_back_from_id", "model_champions", ["rolled_back_from_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_model_champions_action", ["action"])
        batch_op.create_index("ix_model_champions_previous_champion_id", ["previous_champion_id"])
        batch_op.create_index("ix_model_champions_rolled_back_from_id", ["rolled_back_from_id"])
        batch_op.create_index("ix_model_champions_model_name_promoted_at", ["model_name", "promoted_at"])

    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_used_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("revoked_by", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("revocation_reason", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("rotated_from_key_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("rotated_to_key_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("rotation_grace_expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.create_foreign_key("fk_api_keys_rotated_from_key_id", "api_keys", ["rotated_from_key_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_api_keys_rotated_to_key_id", "api_keys", ["rotated_to_key_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_api_keys_expires_at", ["expires_at"])
        batch_op.create_index("ix_api_keys_last_used_at", ["last_used_at"])
        batch_op.create_index("ix_api_keys_is_active_expires_at", ["is_active", "expires_at"])
        batch_op.create_index("ix_api_keys_rotated_from_key_id", ["rotated_from_key_id"])
        batch_op.create_index("ix_api_keys_rotated_to_key_id", ["rotated_to_key_id"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.String(length=256), nullable=True),
        sa.Column("drift_report_id", sa.String(), nullable=True),
        sa.Column("drift_run_id", sa.String(), nullable=True),
        sa.Column("evaluation_run_id", sa.String(), nullable=True),
        sa.Column("message", sa.String(length=2048), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=256), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(["drift_report_id"], ["drift_reports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["drift_run_id"], ["drift_job_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_events_dedupe_key"), "alert_events", ["dedupe_key"], unique=False)
    op.create_index(op.f("ix_alert_events_drift_report_id"), "alert_events", ["drift_report_id"], unique=False)
    op.create_index(op.f("ix_alert_events_drift_run_id"), "alert_events", ["drift_run_id"], unique=False)
    op.create_index(op.f("ix_alert_events_evaluation_run_id"), "alert_events", ["evaluation_run_id"], unique=False)
    op.create_index(op.f("ix_alert_events_event_type"), "alert_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_alert_events_model_name"), "alert_events", ["model_name"], unique=False)
    op.create_index(op.f("ix_alert_events_status"), "alert_events", ["status"], unique=False)
    op.create_index("ix_alert_events_status_created_at", "alert_events", ["status", "created_at"], unique=False)
    op.create_index("ix_alert_events_model_name_created_at", "alert_events", ["model_name", "created_at"], unique=False)

    op.create_table(
        "production_prediction_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("records", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("received_by", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_prediction_batches_model_name"), "production_prediction_batches", ["model_name"], unique=False)
    op.create_index("ix_prediction_batches_model_created_at", "production_prediction_batches", ["model_name", "created_at"], unique=False)
    op.create_index("ix_prediction_batches_source_created_at", "production_prediction_batches", ["source", "created_at"], unique=False)

    op.create_table(
        "champion_rollbacks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("from_champion_id", sa.String(), nullable=True),
        sa.Column("to_champion_id", sa.String(), nullable=True),
        sa.Column("from_run_id", sa.String(), nullable=False),
        sa.Column("to_run_id", sa.String(), nullable=False),
        sa.Column("actor", sa.String(length=256), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=False),
        sa.Column("validation_status", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rollback_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["from_champion_id"], ["model_champions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_champion_id"], ["model_champions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_champion_rollbacks_model_name"), "champion_rollbacks", ["model_name"], unique=False)
    op.create_index(op.f("ix_champion_rollbacks_from_champion_id"), "champion_rollbacks", ["from_champion_id"], unique=False)
    op.create_index(op.f("ix_champion_rollbacks_to_champion_id"), "champion_rollbacks", ["to_champion_id"], unique=False)
    op.create_index("ix_champion_rollbacks_model_created_at", "champion_rollbacks", ["model_name", "created_at"], unique=False)

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("status_code", existing_type=sa.String(length=16), type_=sa.Integer(), existing_nullable=True)
        batch_op.add_column(sa.Column("api_key_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("actor_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("resource_type", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("resource_id", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("action", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("correlation_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("error_code", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("duration_ms", sa.Float(), nullable=True))
        batch_op.create_foreign_key("fk_audit_logs_api_key_id", "api_keys", ["api_key_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_audit_logs_api_key_id", ["api_key_id"])
        batch_op.create_index("ix_audit_logs_action", ["action"])
        batch_op.create_index("ix_audit_logs_correlation_id", ["correlation_id"])
        batch_op.create_index("ix_audit_logs_error_code", ["error_code"])
        batch_op.create_index("ix_audit_logs_timestamp", ["timestamp"])
        batch_op.create_index("ix_audit_logs_user_timestamp", ["user", "timestamp"])
        batch_op.create_index("ix_audit_logs_resource_type_resource_id", ["resource_type", "resource_id"])


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_index("ix_audit_logs_resource_type_resource_id")
        batch_op.drop_index("ix_audit_logs_user_timestamp")
        batch_op.drop_index("ix_audit_logs_timestamp")
        batch_op.drop_index("ix_audit_logs_error_code")
        batch_op.drop_index("ix_audit_logs_correlation_id")
        batch_op.drop_index("ix_audit_logs_action")
        batch_op.drop_index("ix_audit_logs_api_key_id")
        batch_op.drop_constraint("fk_audit_logs_api_key_id", type_="foreignkey")
        for column in ["duration_ms", "error_code", "correlation_id", "action", "resource_id", "resource_type", "actor_type", "api_key_id"]:
            batch_op.drop_column(column)
        batch_op.alter_column("status_code", existing_type=sa.Integer(), type_=sa.String(length=16), existing_nullable=True)

    op.drop_index("ix_champion_rollbacks_model_created_at", table_name="champion_rollbacks")
    op.drop_index(op.f("ix_champion_rollbacks_to_champion_id"), table_name="champion_rollbacks")
    op.drop_index(op.f("ix_champion_rollbacks_from_champion_id"), table_name="champion_rollbacks")
    op.drop_index(op.f("ix_champion_rollbacks_model_name"), table_name="champion_rollbacks")
    op.drop_table("champion_rollbacks")

    op.drop_index("ix_prediction_batches_source_created_at", table_name="production_prediction_batches")
    op.drop_index("ix_prediction_batches_model_created_at", table_name="production_prediction_batches")
    op.drop_index(op.f("ix_production_prediction_batches_model_name"), table_name="production_prediction_batches")
    op.drop_table("production_prediction_batches")

    op.drop_index("ix_alert_events_model_name_created_at", table_name="alert_events")
    op.drop_index("ix_alert_events_status_created_at", table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_status"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_model_name"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_event_type"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_evaluation_run_id"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_drift_run_id"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_drift_report_id"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_dedupe_key"), table_name="alert_events")
    op.drop_table("alert_events")

    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.drop_index("ix_api_keys_rotated_to_key_id")
        batch_op.drop_index("ix_api_keys_rotated_from_key_id")
        batch_op.drop_index("ix_api_keys_is_active_expires_at")
        batch_op.drop_index("ix_api_keys_last_used_at")
        batch_op.drop_index("ix_api_keys_expires_at")
        batch_op.drop_constraint("fk_api_keys_rotated_to_key_id", type_="foreignkey")
        batch_op.drop_constraint("fk_api_keys_rotated_from_key_id", type_="foreignkey")
        for column in ["updated_at", "rotation_grace_expires_at", "rotated_to_key_id", "rotated_from_key_id", "revocation_reason", "revoked_by", "use_count", "last_used_at", "expires_at"]:
            batch_op.drop_column(column)

    with op.batch_alter_table("model_champions") as batch_op:
        batch_op.drop_index("ix_model_champions_model_name_promoted_at")
        batch_op.drop_index("ix_model_champions_rolled_back_from_id")
        batch_op.drop_index("ix_model_champions_previous_champion_id")
        batch_op.drop_index("ix_model_champions_action")
        batch_op.drop_constraint("fk_model_champions_rolled_back_from_id", type_="foreignkey")
        batch_op.drop_constraint("fk_model_champions_previous_champion_id", type_="foreignkey")
        for column in ["lifecycle_metadata", "rollback_at", "rollback_reason", "rolled_back_from_id", "action", "previous_champion_id"]:
            batch_op.drop_column(column)

    with op.batch_alter_table("drift_reports") as batch_op:
        batch_op.drop_index("ix_drift_reports_is_alerting_created_at")
        batch_op.drop_index("ix_drift_reports_model_name_created_at")
        batch_op.drop_index("ix_drift_reports_run_id")
        batch_op.drop_index("ix_drift_reports_job_id")
        batch_op.drop_constraint("fk_drift_reports_run_id_drift_job_runs", type_="foreignkey")
        batch_op.drop_constraint("fk_drift_reports_job_id_drift_jobs", type_="foreignkey")
        batch_op.drop_column("run_id")
        batch_op.drop_column("job_id")

    op.drop_index("ix_drift_job_runs_status_created_at", table_name="drift_job_runs")
    op.drop_index("ix_drift_job_runs_model_name_created_at", table_name="drift_job_runs")
    op.drop_index(op.f("ix_drift_job_runs_model_name"), table_name="drift_job_runs")
    op.drop_index(op.f("ix_drift_job_runs_job_id"), table_name="drift_job_runs")
    op.drop_table("drift_job_runs")

    op.drop_index("ix_drift_jobs_status_next_run_at", table_name="drift_jobs")
    op.drop_index(op.f("ix_drift_jobs_model_name"), table_name="drift_jobs")
    op.drop_table("drift_jobs")

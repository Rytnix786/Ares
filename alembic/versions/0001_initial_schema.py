from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("evaluation_runs", sa.Column("id", sa.String(), nullable=False), sa.Column("commit_sha", sa.String(length=64), nullable=False), sa.Column("model_name", sa.String(length=256), nullable=False), sa.Column("model_version", sa.String(length=128), nullable=False), sa.Column("branch", sa.String(length=256), nullable=False), sa.Column("pr_number", sa.Integer(), nullable=True), sa.Column("overall_f1", sa.Float(), nullable=False), sa.Column("overall_accuracy", sa.Float(), nullable=False), sa.Column("overall_precision", sa.Float(), nullable=False), sa.Column("overall_recall", sa.Float(), nullable=False), sa.Column("latency_p50_ms", sa.Float(), nullable=False), sa.Column("latency_p99_ms", sa.Float(), nullable=False), sa.Column("model_size_mb", sa.Float(), nullable=False), sa.Column("slice_metrics", sa.JSON(), nullable=False), sa.Column("gate_config_snapshot", sa.JSON(), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False), sa.Column("failure_reason", sa.String(length=2048), nullable=True), sa.Column("golden_set_version", sa.String(length=64), nullable=False), sa.Column("n_samples_evaluated", sa.Integer(), nullable=False), sa.Column("duration_seconds", sa.Float(), nullable=False), sa.Column("mlflow_run_id", sa.String(length=256), nullable=True), sa.Column("artifact_uri", sa.String(length=2048), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("commit_sha", "golden_set_version", "model_name", name="uq_evaluation_idempotency"))
    op.create_index(op.f("ix_evaluation_runs_commit_sha"), "evaluation_runs", ["commit_sha"], unique=False)
    op.create_index(op.f("ix_evaluation_runs_model_name"), "evaluation_runs", ["model_name"], unique=False)
    op.create_table("model_champions", sa.Column("id", sa.String(), nullable=False), sa.Column("model_name", sa.String(length=256), nullable=False), sa.Column("champion_run_id", sa.String(), nullable=False), sa.Column("promoted_at", sa.DateTime(), nullable=False), sa.Column("promoted_by", sa.String(length=256), nullable=False), sa.Column("promotion_reason", sa.String(length=1024), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False), sa.ForeignKeyConstraint(["champion_run_id"], ["evaluation_runs.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_model_champions_model_name"), "model_champions", ["model_name"], unique=False)
    op.create_index("uq_active_champion_per_model", "model_champions", ["model_name"], unique=True, postgresql_where=sa.text("is_active = true"))
    op.create_table("drift_reports", sa.Column("id", sa.String(), nullable=False), sa.Column("model_name", sa.String(length=256), nullable=False), sa.Column("feature", sa.String(length=256), nullable=False), sa.Column("kl_divergence", sa.Float(), nullable=False), sa.Column("psi", sa.Float(), nullable=False), sa.Column("is_alerting", sa.Boolean(), nullable=False), sa.Column("severity", sa.String(length=32), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_drift_reports_model_name"), "drift_reports", ["model_name"], unique=False)


def downgrade() -> None:
    op.drop_table("drift_reports")
    op.drop_index("uq_active_champion_per_model", table_name="model_champions")
    op.drop_table("model_champions")
    op.drop_table("evaluation_runs")
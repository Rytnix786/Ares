from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_phase2_product_completeness"
down_revision = "0006_operational_lifecycle_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slice_metric_points",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("slice_name", sa.String(length=256), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_slice_metric_points_run_id"), "slice_metric_points", ["run_id"], unique=False)
    op.create_index(op.f("ix_slice_metric_points_model_name"), "slice_metric_points", ["model_name"], unique=False)
    op.create_index(op.f("ix_slice_metric_points_slice_name"), "slice_metric_points", ["slice_name"], unique=False)
    op.create_index(op.f("ix_slice_metric_points_metric_name"), "slice_metric_points", ["metric_name"], unique=False)
    op.create_index("ix_slice_metric_points_model_slice_metric", "slice_metric_points", ["model_name", "slice_name", "metric_name", "created_at"], unique=False)
    op.create_index("ix_slice_metric_points_critical_created_at", "slice_metric_points", ["is_critical", "created_at"], unique=False)

    with op.batch_alter_table("evaluation_runs") as batch_op:
        batch_op.add_column(sa.Column("evaluator_name", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("evaluator_version", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("model_card_uri", sa.String(length=2048), nullable=True))
        batch_op.add_column(sa.Column("model_card_json", sa.JSON(), nullable=True))
        batch_op.create_index("ix_evaluation_runs_evaluator_name", ["evaluator_name"])
        batch_op.create_index("ix_evaluation_runs_model_card_uri", ["model_card_uri"])


def downgrade() -> None:
    with op.batch_alter_table("evaluation_runs") as batch_op:
        batch_op.drop_index("ix_evaluation_runs_model_card_uri")
        batch_op.drop_index("ix_evaluation_runs_evaluator_name")
        for column in ["model_card_json", "model_card_uri", "evaluator_version", "evaluator_name"]:
            batch_op.drop_column(column)

    op.drop_index("ix_slice_metric_points_critical_created_at", table_name="slice_metric_points")
    op.drop_index("ix_slice_metric_points_model_slice_metric", table_name="slice_metric_points")
    op.drop_index(op.f("ix_slice_metric_points_metric_name"), table_name="slice_metric_points")
    op.drop_index(op.f("ix_slice_metric_points_slice_name"), table_name="slice_metric_points")
    op.drop_index(op.f("ix_slice_metric_points_model_name"), table_name="slice_metric_points")
    op.drop_index(op.f("ix_slice_metric_points_run_id"), table_name="slice_metric_points")
    op.drop_table("slice_metric_points")

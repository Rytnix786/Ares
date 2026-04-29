from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_mlflow_status_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluation_runs", sa.Column("mlflow_status", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("evaluation_runs", sa.Column("mlflow_error", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluation_runs", "mlflow_error")
    op.drop_column("evaluation_runs", "mlflow_status")
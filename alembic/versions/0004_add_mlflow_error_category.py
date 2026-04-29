from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_add_mlflow_error_category"
down_revision = "0003_add_api_keys_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_runs",
        sa.Column("mlflow_error_category", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "mlflow_error_category")

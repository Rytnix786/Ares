from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_add_webhooks_table"
down_revision = "0004_add_mlflow_error_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("secret", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhooks_event_type"), "webhooks", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_webhooks_event_type"), table_name="webhooks")
    op.drop_table("webhooks")

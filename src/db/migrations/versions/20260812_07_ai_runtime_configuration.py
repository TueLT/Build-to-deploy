"""Persist the AI provider and model selected by a platform admin."""

import sqlalchemy as sa

from alembic import op

revision = "20260812_07"
down_revision = "20260806_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if "platform_settings" in set(sa.inspect(connection).get_table_names()):
        return
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")

"""Remove workspace authorization and keep platform roles plus user ownership.

Conversation contents remain intact. Access is enforced only by active registered-user
participants; platform administrators intentionally receive no conversation-reading bypass.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260813_08"
down_revision = "20260812_07"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _drop_column(table: str, column: str) -> None:
    if table not in _table_names() or column not in _columns(table):
        return
    with op.batch_alter_table(table) as batch:
        batch.drop_column(column)


def upgrade() -> None:
    tables = _table_names()

    if "conversation_participants" in tables:
        columns = _columns("conversation_participants")
        if "external_contact_id" in columns:
            op.execute(sa.text("DELETE FROM conversation_participants WHERE user_id IS NULL"))
        # Recreate the participant table without external principals or workspace-specific kinds.
        with op.batch_alter_table("conversation_participants", recreate="always") as batch:
            if "principal_kind" in columns:
                batch.drop_column("principal_kind")
            if "external_contact_id" in columns:
                batch.drop_column("external_contact_id")
            batch.alter_column("user_id", existing_type=sa.String(), nullable=False)

    # These features were workspace-only and their UI had already been removed.
    for table in (
        "people_preferences",
        "contact_relationships",
        "external_contacts",
        "support_access_grants",
        "workspace_memberships",
        "migration_states",
    ):
        if table in _table_names():
            op.drop_table(table)

    for table in ("audit_logs", "conversations", "tasks", "usage_logs", "memories", "reminders"):
        _drop_column(table, "workspace_id")

    _drop_column("users", "role")

    if "workspaces" in _table_names():
        op.drop_table("workspaces")

    # Replace workspace-prefixed indexes with direct owner/time indexes.
    inspector = sa.inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes("tasks")} if "tasks" in _table_names() else set()
    if "tasks" in _table_names():
        if "ix_tasks_owner_status" not in existing:
            op.create_index("ix_tasks_owner_status", "tasks", ["owner_id", "status"])
        if "ix_tasks_due_at" not in existing:
            op.create_index("ix_tasks_due_at", "tasks", ["due_at"])

    existing = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("memories")} if "memories" in _table_names() else set()
    if "memories" in _table_names() and "ix_memories_owner_created" not in existing:
        op.create_index("ix_memories_owner_created", "memories", ["owner_id", "created_at"])

    existing = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("reminders")} if "reminders" in _table_names() else set()
    if "reminders" in _table_names():
        if "ix_reminders_owner_status" not in existing:
            op.create_index("ix_reminders_owner_status", "reminders", ["owner_id", "status"])
        if "ix_reminders_fire_at" not in existing:
            op.create_index("ix_reminders_fire_at", "reminders", ["fire_at"])


def downgrade() -> None:
    raise RuntimeError(
        "20260813_08 is intentionally irreversible: workspace memberships and external-contact "
        "principals cannot be reconstructed safely. Restore a database backup to roll back."
    )

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


def _uuid() -> str:
    return uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    display_name: Mapped[str]
    role: Mapped[str] = mapped_column(default="user")  # "user" | "admin"
    platform_role: Mapped[str] = mapped_column(default="user")  # "user" | "platform_admin"
    is_active: Mapped[bool] = mapped_column(default=True)
    job_title: Mapped[str] = mapped_column(default="")
    timezone: Mapped[str] = mapped_column(default="Asia/Ho_Chi_Minh")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("type IN ('personal', 'organization')", name="ck_workspace_type"),
        CheckConstraint("status IN ('active', 'suspended', 'deleting')", name="ck_workspace_status"),
        CheckConstraint(
            "(type = 'personal' AND personal_owner_user_id IS NOT NULL) OR "
            "(type = 'organization' AND personal_owner_user_id IS NULL)",
            name="ck_workspace_owner_matches_type",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    type: Mapped[str]
    name: Mapped[str]
    slug: Mapped[str | None] = mapped_column(default=None, unique=True)
    personal_owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), default=None, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership_user"),
        CheckConstraint("role IN ('owner', 'admin', 'member', 'guest')", name="ck_workspace_membership_role"),
        CheckConstraint(
            "status IN ('active', 'invited', 'suspended', 'revoked')",
            name="ck_workspace_membership_status",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str]
    status: Mapped[str] = mapped_column(default="active")
    invited_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ExternalContact(Base):
    __tablename__ = "external_contacts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_external_contact_workspace_email"),
        CheckConstraint("status IN ('invited', 'active', 'revoked')", name="ck_external_contact_status"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    email: Mapped[str]
    display_name: Mapped[str]
    organization: Mapped[str | None] = mapped_column(default=None)
    linked_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None, index=True)
    status: Mapped[str] = mapped_column(default="invited")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ContactRelationship(Base):
    """A user's private, directional relationship to a person in one workspace."""

    __tablename__ = "contact_relationships"
    __table_args__ = (
        CheckConstraint(
            "((subject_user_id IS NOT NULL) AND (subject_external_contact_id IS NULL)) OR "
            "((subject_user_id IS NULL) AND (subject_external_contact_id IS NOT NULL))",
            name="ck_contact_relationship_exactly_one_subject",
        ),
        CheckConstraint(
            "(subject_kind = 'workspace_user' AND subject_user_id IS NOT NULL "
            "AND subject_external_contact_id IS NULL) OR "
            "(subject_kind = 'external_contact' AND subject_user_id IS NULL "
            "AND subject_external_contact_id IS NOT NULL)",
            name="ck_contact_relationship_kind_matches_subject",
        ),
        CheckConstraint("strength >= 1 AND strength <= 5", name="ck_contact_relationship_strength"),
        CheckConstraint(
            "relationship_type IN ('colleague', 'manager', 'direct_report', 'client', 'partner', "
            "'vendor', 'friend', 'mentor', 'other')",
            name="ck_contact_relationship_type",
        ),
        CheckConstraint(
            "status IN ('suggested', 'active', 'archived', 'rejected')",
            name="ck_contact_relationship_status",
        ),
        CheckConstraint(
            "source IN ('manual', 'ai_suggested', 'imported')",
            name="ck_contact_relationship_source",
        ),
        CheckConstraint(
            "subject_user_id IS NULL OR owner_user_id <> subject_user_id",
            name="ck_contact_relationship_not_self",
        ),
        Index(
            "uq_contact_relationship_workspace_user",
            "workspace_id",
            "owner_user_id",
            "subject_user_id",
            unique=True,
            sqlite_where=text("subject_user_id IS NOT NULL"),
            postgresql_where=text("subject_user_id IS NOT NULL"),
        ),
        Index(
            "uq_contact_relationship_external",
            "workspace_id",
            "owner_user_id",
            "subject_external_contact_id",
            unique=True,
            sqlite_where=text("subject_external_contact_id IS NOT NULL"),
            postgresql_where=text("subject_external_contact_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    subject_kind: Mapped[str]
    subject_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None, index=True)
    subject_external_contact_id: Mapped[str | None] = mapped_column(
        ForeignKey("external_contacts.id"), default=None, index=True
    )
    relationship_type: Mapped[str]
    custom_label: Mapped[str | None] = mapped_column(default=None)
    strength: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(default="active")
    source: Mapped[str] = mapped_column(default="manual")
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MigrationState(Base):
    __tablename__ = "migration_states"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    migration_key: Mapped[str] = mapped_column(unique=True, index=True)
    migration_version: Mapped[str] = mapped_column(default="workspace_foundation_v1")
    status: Mapped[str]
    error_code: Mapped[str | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class SupportAccessGrant(Base):
    __tablename__ = "support_access_grants"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    platform_admin_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    requested_scope: Mapped[str]
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default="requested")
    approved_by_owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"), default=None, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None, index=True)
    actor_type: Mapped[str]
    action: Mapped[str]
    target_type: Mapped[str]
    target_id: Mapped[str | None] = mapped_column(default=None)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (CheckConstraint("type IN ('direct', 'group')", name="ck_conversation_type"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    type: Mapped[str]  # "direct" | "group"
    name: Mapped[str | None] = mapped_column(default=None)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    participants: Mapped[list["ConversationParticipant"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        CheckConstraint(
            "((user_id IS NOT NULL) AND (external_contact_id IS NULL)) OR "
            "((user_id IS NULL) AND (external_contact_id IS NOT NULL))",
            name="ck_conversation_participant_exactly_one_principal",
        ),
        CheckConstraint(
            "(principal_kind = 'workspace_user' AND user_id IS NOT NULL AND external_contact_id IS NULL) OR "
            "(principal_kind = 'external_contact' AND user_id IS NULL AND external_contact_id IS NOT NULL)",
            name="ck_conversation_participant_kind_matches_principal",
        ),
        CheckConstraint(
            "resource_role IN ('manager', 'participant', 'viewer')",
            name="ck_conversation_participant_resource_role",
        ),
        Index(
            "uq_conversation_participant_user",
            "conversation_id",
            "user_id",
            unique=True,
            sqlite_where=text("user_id IS NOT NULL"),
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_conversation_participant_external",
            "conversation_id",
            "external_contact_id",
            unique=True,
            sqlite_where=text("external_contact_id IS NOT NULL"),
            postgresql_where=text("external_contact_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    principal_kind: Mapped[str] = mapped_column(default="workspace_user")
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None, index=True)
    external_contact_id: Mapped[str | None] = mapped_column(
        ForeignKey("external_contacts.id"), default=None, index=True
    )
    resource_role: Mapped[str] = mapped_column(default="participant")
    invited_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    conversation: Mapped["Conversation"] = relationship(back_populates="participants")
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), default=None)
    title: Mapped[str]
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    priority: Mapped[str] = mapped_column(default="Medium")  # "High" | "Medium" | "Low"
    status: Mapped[str] = mapped_column(default="suggested")
    # "suggested" | "pending" | "in_progress" | "completed" | "dismissed"
    source: Mapped[str] = mapped_column(default="manual")  # "manual" | "proactive"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped["User"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    provider: Mapped[str]
    model: Mapped[str]
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(default="Preference")  # "Work" | "Preference" | "People" | ...
    title: Mapped[str]
    detail: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped["User"] = relationship()


class CalendarSyncState(Base):
    """Single-row table (id is always "default") holding the Google Calendar incremental sync
    cursor, so calendar_service.poll_calendar_changes can resume where it left off across polls
    and server restarts instead of re-scanning the whole calendar every time."""

    __tablename__ = "calendar_sync_state"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: "default")
    sync_token: Mapped[str | None] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None, index=True)
    title: Mapped[str]
    message: Mapped[str] = mapped_column(default="")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default="scheduled")  # "scheduled" | "fired" | "cancelled"
    source: Mapped[str] = mapped_column(default="manual")  # "manual" | "agent"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped["User | None"] = relationship()

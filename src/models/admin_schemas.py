from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AdminUserOut(BaseModel):
    id: str
    email: str
    display_name: str
    platform_role: Literal["user", "platform_admin"]
    is_active: bool
    created_at: datetime


class AdminHealthComponent(BaseModel):
    key: str
    label: str
    status: Literal["operational", "degraded", "down"]
    detail: str


class AdminSystemHealth(BaseModel):
    overall_status: Literal["operational", "degraded", "down"]
    checked_at: datetime
    components: list[AdminHealthComponent]


class AdminAIManagement(BaseModel):
    provider: str
    model: str
    temperature: float
    daily_token_budget: int
    llm_configured: bool
    human_confirmation_required: bool
    conversation_consent_required: bool
    granted_permissions: int
    revoked_permissions: int
    proactive_suggestions: int
    proactive_accepted: int
    proactive_dismissed: int
    configured_providers: list[str]
    model_options: dict[str, list[dict[str, str]]]


class UpdateAIConfigurationRequest(BaseModel):
    provider: Literal["google", "groq", "openai"]
    model: str = Field(min_length=1, max_length=120)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AdminUsageTotals(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    request_count: int
    estimated_cost_usd: float
    unpriced_tokens: int


class AdminUsageDay(AdminUsageTotals):
    date: date


class AdminUsageModel(AdminUsageTotals):
    provider: str
    model: str


class AdminAIUsageReport(BaseModel):
    days: int
    since: datetime
    totals: AdminUsageTotals
    daily: list[AdminUsageDay]
    models: list[AdminUsageModel]


class AdminAuditLogOut(BaseModel):
    id: str
    actor_user_id: str | None
    actor_email: str | None
    actor_display_name: str | None
    actor_type: str
    action: str
    target_type: str
    target_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


class AdminAuditLogPage(BaseModel):
    total: int
    items: list[AdminAuditLogOut]


class UpdateRoleRequest(BaseModel):
    role: Literal["user", "admin"]


class UpdateStatusRequest(BaseModel):
    is_active: bool

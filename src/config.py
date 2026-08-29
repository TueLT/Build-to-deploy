from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    company_name: str = "Orbit"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = ""
    cors_origin_regex: str = ""

    # LLM
    llm_provider: Literal["google", "groq", "openai", "openrouter"] = "google"
    google_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "http://localhost:5173"
    openrouter_app_name: str = "Orbit"
    openrouter_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    model_name: str = "gemini-2.5-flash"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_output_tokens: int = Field(default=384, ge=128, le=8_192)
    # Workspace specialists inherit provider/model credentials from the shared
    # LLM settings unless explicitly overridden.  Their generation settings
    # stay conservative because they explain deterministic business state.
    product_delivery_llm_provider: Literal["google", "groq", "openai", "openrouter"] | None = None
    product_delivery_model_name: str | None = None
    product_delivery_llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    product_delivery_llm_max_output_tokens: int = Field(default=1_536, ge=128, le=8_192)
    product_delivery_llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    # Routing is latency-sensitive but must not share the specialist quota by
    # accident. By default it inherits the Product Delivery synthesis model.
    product_delivery_routing_llm_provider: Literal["google", "groq", "openai", "openrouter"] | None = None
    product_delivery_routing_model_name: str | None = None
    product_delivery_routing_llm_temperature: float = Field(default=0.0, ge=0.0, le=0.5)
    product_delivery_routing_llm_max_output_tokens: int = Field(default=384, ge=128, le=1_024)
    product_delivery_routing_llm_timeout_seconds: float = Field(default=8.0, ge=1.0, le=30.0)
    product_delivery_routing_llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    product_delivery_conversation_llm_enabled: bool = True
    product_delivery_conversation_llm_timeout_seconds: float = Field(default=12.0, ge=1.0, le=45.0)
    quality_assurance_llm_provider: Literal["google", "groq", "openai", "openrouter"] | None = None
    quality_assurance_model_name: str | None = None
    quality_assurance_llm_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    quality_assurance_llm_max_output_tokens: int = Field(default=1_024, ge=128, le=8_192)
    workspace_agent_verifier_enabled: bool = False
    workspace_agent_verifier_provider: Literal["google", "groq", "openai", "openrouter"] | None = None
    workspace_agent_verifier_model_name: str | None = None
    workspace_agent_verifier_temperature: float = Field(default=0.0, ge=0.0, le=0.5)
    workspace_agent_verifier_max_output_tokens: int = Field(default=256, ge=64, le=2_048)
    daily_token_budget: int = Field(default=200_000, ge=0)
    agent_max_thread_messages: int = Field(default=20, ge=6, le=100)
    agent_thread_summary_chars: int = Field(default=6000, ge=1000, le=20000)
    agent_thread_retention_days: int = Field(default=30, ge=1, le=365)

    # Multi-agent rollout. All profiles stay off until their policy/data foundations are ready.
    multi_agent_enabled: bool = False
    product_delivery_agent_enabled: bool = False
    product_delivery_hybrid_router_enabled: bool = True
    product_delivery_supervisor_enabled: bool = True
    product_delivery_task_specialist_enabled: bool = True
    product_delivery_risk_specialist_enabled: bool = True
    product_delivery_planning_specialist_enabled: bool = True
    product_delivery_evidence_specialist_enabled: bool = True
    product_delivery_capacity_specialist_enabled: bool = False
    product_delivery_multi_specialist_workflows_enabled: bool = True
    product_delivery_specialist_llm_enabled: bool = True
    product_delivery_specialist_llm_provider: Literal["google", "groq", "openai", "openrouter"] | None = None
    product_delivery_specialist_model_name: str | None = None
    product_delivery_specialist_llm_temperature: float = Field(default=0.1, ge=0.0, le=0.5)
    product_delivery_specialist_llm_max_output_tokens: int = Field(default=384, ge=128, le=2_048)
    product_delivery_specialist_llm_timeout_seconds: float = Field(default=6.0, ge=1.0, le=30.0)
    product_delivery_specialist_llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    product_delivery_max_specialists_per_workflow: int = Field(default=4, ge=1, le=4)
    product_delivery_workflow_timeout_seconds: float = Field(default=40.0, ge=2.0, le=120.0)
    quality_assurance_agent_enabled: bool = False
    executive_agent_enabled: bool = False
    workspace_agent_runtime_mode: Literal["embedded", "remote"] = "embedded"
    workspace_agent_runtime_url: str = "http://workspace-agent-product-delivery:8010"
    workspace_agent_progress_callback_url: str = ""
    quality_assurance_runtime_url: str = "http://workspace-agent-quality-assurance:8011"
    workspace_agent_runtime_secret: str = "dev-runtime-secret-change-me"
    quality_assurance_runtime_secret: str = "dev-quality-runtime-secret-change-me"
    workspace_agent_runtime_timeout_seconds: float = Field(default=45.0, ge=1.0, le=120.0)
    workspace_agent_runtime_queue_timeout_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    workspace_agent_max_concurrency: int = Field(default=4, ge=1, le=100)
    workspace_agent_runtime_signature_max_age_seconds: int = Field(default=60, ge=5, le=300)
    workspace_agent_runtime_workspace_id: str = ""
    workspace_agent_runtime_profile: Literal["product_delivery", "quality_assurance"] = "product_delivery"
    workspace_agent_runtime_version: str = "product-delivery-v2"
    quality_assurance_runtime_version: str = "quality-assurance-v2"
    workspace_agent_memory_retention_days: int = Field(default=30, ge=1, le=365)
    workspace_agent_memory_history_limit: int = Field(default=12, ge=2, le=50)
    workspace_agent_memory_max_content_chars: int = Field(default=8_000, ge=512, le=50_000)
    workspace_agent_snapshot_prompt_max_chars: int = Field(default=8_000, ge=4_000, le=100_000)
    workspace_agent_history_prompt_max_chars: int = Field(default=8_000, ge=1_000, le=40_000)
    workspace_agent_memory_cleanup_interval_minutes: int = Field(default=60, ge=5, le=1_440)
    # Enterprise default: organizations are provisioned by platform operations.
    # Keep this switch only for local/demo compatibility and isolated tests.
    allow_self_service_organization_creation: bool = False

    # Database
    database_url: str = "sqlite:///./data/app.db"
    db_pool_size: int = Field(default=3, ge=1, le=100)
    db_max_overflow: int = Field(default=2, ge=0, le=200)
    db_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    agent_checkpointer_pool_size: int = Field(default=2, ge=1, le=10)

    # Auth
    secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    initial_admin_email: str = ""
    bootstrap_owner_user_id: str = ""
    # "Sign in with Google" - Web application OAuth Client ID (audience for ID-token verification).
    # Distinct from the per-user Calendar OAuth client below. No client secret is needed here:
    # this setting only verifies Google Sign-In ID tokens.
    google_oauth_client_id: str = ""

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    # Google Calendar
    google_calendar_client_id: str = ""
    google_calendar_client_secret: str = ""
    google_calendar_redirect_uri: str = "http://localhost:8000/api/v1/calendar/oauth/callback"
    credential_encryption_key: str = ""
    frontend_origin: str = "http://localhost:5173"
    calendar_timezone: str = "Asia/Ho_Chi_Minh"

    # Reminders / scheduler
    scheduler_timezone: str = "Asia/Ho_Chi_Minh"

    # Calendar polling (no public HTTPS URL yet for Google's real push/webhook channels, so
    # changes made directly in Google Calendar are picked up by polling with a syncToken instead)
    calendar_poll_interval_seconds: int = Field(default=20, ge=5)

    # Per-process burst protection. The deployment is intentionally single-worker because
    # WebSocket connections and the scheduler are process-local.
    rate_limit_enabled: bool = True
    rate_limit_auth: str = "10/minute"
    rate_limit_register: str = "5/minute"
    rate_limit_chat: str = "15/minute"
    rate_limit_read: str = "300/minute"
    rate_limit_crud: str = "60/minute"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env != "production":
            return self
        if len(self.secret_key.encode("utf-8")) < 32 or "change-me" in self.secret_key:
            raise ValueError("SECRET_KEY must contain at least 32 bytes of non-placeholder data in production")
        if self.database_url.startswith("sqlite"):
            raise ValueError("Production requires PostgreSQL; SQLite is supported only for development and tests")
        origins = {origin.strip() for origin in self.cors_origins.split(",") if origin.strip()}
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS must explicitly list trusted origins in production")
        if self.cors_origin_regex:
            raise ValueError("CORS_ORIGIN_REGEX must be empty in production; list trusted origins explicitly")
        if self.llm_provider == "google" and not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=google in production")
        if self.llm_provider == "groq" and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq in production")
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai in production")
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter in production")
        configured_workspace_providers = {
            self.product_delivery_llm_provider or self.llm_provider,
            self.product_delivery_routing_llm_provider
            or self.product_delivery_llm_provider
            or self.llm_provider,
            self.quality_assurance_llm_provider or self.llm_provider,
        }
        if self.product_delivery_specialist_llm_enabled:
            configured_workspace_providers.add(
                self.product_delivery_specialist_llm_provider
                or self.product_delivery_llm_provider
                or self.llm_provider
            )
        if self.workspace_agent_verifier_enabled:
            configured_workspace_providers.add(self.workspace_agent_verifier_provider or self.llm_provider)
        if "google" in configured_workspace_providers and not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required by a configured workspace-agent model")
        if "groq" in configured_workspace_providers and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required by a configured workspace-agent model")
        if "openai" in configured_workspace_providers and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required by a configured workspace-agent model")
        if "openrouter" in configured_workspace_providers and not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required by a configured workspace-agent model")
        if (
            self.multi_agent_enabled
            and (self.product_delivery_agent_enabled or self.quality_assurance_agent_enabled)
            and self.workspace_agent_runtime_mode != "remote"
        ):
            raise ValueError("Production workspace agents require WORKSPACE_AGENT_RUNTIME_MODE=remote")
        if self.workspace_agent_runtime_mode == "remote" and (
            len(self.workspace_agent_runtime_secret.encode("utf-8")) < 32
            or "change-me" in self.workspace_agent_runtime_secret
        ):
            raise ValueError("Remote workspace agent runtime requires a strong internal secret")
        if self.workspace_agent_runtime_mode == "remote" and (
            len(self.quality_assurance_runtime_secret.encode("utf-8")) < 32
            or "change-me" in self.quality_assurance_runtime_secret
        ):
            raise ValueError("Remote Quality runtime requires a strong internal secret")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

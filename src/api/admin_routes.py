from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_admin
from src.config import get_settings
from src.db.models import (
    AIPermission,
    AuditLog,
    GoogleCalendarCredential,
    PlatformSetting,
    Task,
    User,
)
from src.db.session import get_db
from src.models.admin_schemas import (
    AdminAIManagement,
    AdminAIUsageReport,
    AdminAuditLogOut,
    AdminAuditLogPage,
    AdminSystemHealth,
    AdminUserOut,
    UpdateAIConfigurationRequest,
    UpdateRoleRequest,
    UpdateStatusRequest,
)
from src.services import ai_config_service, usage_service
from src.services.audit_service import record_audit_event
from src.services.scheduler import scheduler
from src.websocket.manager import manager

router = APIRouter(dependencies=[Depends(require_admin)])


async def _get_user_or_404(user_id: str, db: AsyncSession) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/system-health", response_model=AdminSystemHealth)
async def get_system_health(db: AsyncSession = Depends(get_db)) -> AdminSystemHealth:
    settings = get_settings()
    components: list[dict[str, str]] = []

    try:
        await db.execute(select(1))
        dialect = db.get_bind().dialect.name
        components.append({"key": "database", "label": "Database", "status": "operational", "detail": f"{dialect} connected"})
    except Exception:  # noqa: BLE001 - health response must describe a failed dependency
        components.append({"key": "database", "label": "Database", "status": "down", "detail": "Connection failed"})

    scheduler_running = scheduler.running
    scheduler_jobs = len(scheduler.get_jobs()) if scheduler_running else 0
    components.append({
        "key": "scheduler",
        "label": "Scheduler",
        "status": "operational" if scheduler_running else "degraded",
        "detail": f"Running with {scheduler_jobs} jobs" if scheduler_running else "Not running",
    })

    active_connections = sum(len(connections) for connections in manager.active.values())
    components.append({
        "key": "websocket",
        "label": "WebSocket",
        "status": "operational",
        "detail": f"{active_connections} active connections across {len(manager.active)} users",
    })

    provider_keys = {
        "google": settings.google_api_key,
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
    }
    llm_configured = bool(provider_keys[settings.llm_provider])
    components.append({
        "key": "llm",
        "label": "LLM provider",
        "status": "operational" if llm_configured else "degraded",
        "detail": f"{settings.llm_provider} / {settings.model_name}" if llm_configured else f"{settings.llm_provider} credential missing",
    })

    calendar_configured = all((
        settings.google_calendar_client_id,
        settings.google_calendar_client_secret,
        settings.credential_encryption_key,
    ))
    connected_calendars = (
        await db.execute(select(func.count()).select_from(GoogleCalendarCredential))
    ).scalar_one()
    components.append({
        "key": "calendar",
        "label": "Google Calendar",
        "status": "operational" if calendar_configured else "degraded",
        "detail": f"Configured; {connected_calendars} connected accounts" if calendar_configured else "OAuth integration not fully configured",
    })

    statuses = {component["status"] for component in components}
    overall_status = "down" if "down" in statuses else "degraded" if "degraded" in statuses else "operational"
    return AdminSystemHealth(
        overall_status=overall_status,
        checked_at=datetime.now(UTC),
        components=components,
    )


@router.get("/ai-management", response_model=AdminAIManagement)
async def get_ai_management(db: AsyncSession = Depends(get_db)) -> AdminAIManagement:
    settings = get_settings()
    provider_keys = {
        "google": settings.google_api_key,
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
    }
    granted_permissions = (
        await db.execute(select(func.count()).select_from(AIPermission).where(AIPermission.granted.is_(True)))
    ).scalar_one()
    revoked_permissions = (
        await db.execute(select(func.count()).select_from(AIPermission).where(AIPermission.granted.is_(False)))
    ).scalar_one()
    proactive_suggestions = (
        await db.execute(select(func.count()).select_from(Task).where(Task.source == "proactive"))
    ).scalar_one()
    proactive_accepted = (
        await db.execute(
            select(func.count()).select_from(Task).where(
                Task.source == "proactive",
                Task.status.in_(("pending", "in_progress", "completed")),
            )
        )
    ).scalar_one()
    proactive_dismissed = (
        await db.execute(
            select(func.count()).select_from(Task).where(Task.source == "proactive", Task.status == "dismissed")
        )
    ).scalar_one()
    return AdminAIManagement(
        provider=settings.llm_provider,
        model=settings.model_name,
        temperature=settings.llm_temperature,
        daily_token_budget=settings.daily_token_budget,
        llm_configured=bool(provider_keys[settings.llm_provider]),
        human_confirmation_required=True,
        conversation_consent_required=True,
        granted_permissions=granted_permissions,
        revoked_permissions=revoked_permissions,
        proactive_suggestions=proactive_suggestions,
        proactive_accepted=proactive_accepted,
        proactive_dismissed=proactive_dismissed,
        configured_providers=ai_config_service.configured_providers(),
        model_options=ai_config_service.MODEL_OPTIONS,
    )


@router.patch("/ai-management", response_model=AdminAIManagement)
async def update_ai_management(
    request: UpdateAIConfigurationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminAIManagement:
    if request.provider not in ai_config_service.configured_providers():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"API key for {request.provider} is not configured",
        )
    if not ai_config_service.is_supported_model(request.provider, request.model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported model for the selected provider",
        )

    settings = get_settings()
    previous = {
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "temperature": settings.llm_temperature,
    }
    value = {
        "provider": request.provider,
        "model": request.model,
        "temperature": request.temperature,
    }
    setting = await db.get(PlatformSetting, ai_config_service.AI_CONFIGURATION_KEY)
    if setting is None:
        setting = PlatformSetting(
            key=ai_config_service.AI_CONFIGURATION_KEY,
            value_json=value,
            updated_by_user_id=current_user.id,
        )
        db.add(setting)
    else:
        setting.value_json = value
        setting.updated_by_user_id = current_user.id
        setting.updated_at = datetime.now(UTC)
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.ai_model_changed",
        target_type="ai_configuration",
        target_id=request.model,
        metadata={"previous": previous, "current": value},
    )
    await db.commit()
    ai_config_service.apply_ai_configuration(request.provider, request.model, request.temperature)
    return await get_ai_management(db)


@router.get("/ai-usage", response_model=AdminAIUsageReport)
async def get_ai_usage(days: int = Query(default=7, ge=1, le=30)) -> AdminAIUsageReport:
    return AdminAIUsageReport.model_validate(await usage_service.get_usage_report(days))


@router.get("/audit-log", response_model=AdminAuditLogPage)
async def list_audit_log(
    q: str | None = None,
    actor_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> AdminAuditLogPage:
    stmt = select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_user_id)
    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(
            AuditLog.action.ilike(pattern)
            | AuditLog.target_type.ilike(pattern)
            | AuditLog.target_id.ilike(pattern)
            | User.email.ilike(pattern)
        )
    if actor_type:
        conditions.append(AuditLog.actor_type == actor_type)
    if conditions:
        stmt = stmt.where(*conditions)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit))
    ).all()
    return AdminAuditLogPage(
        total=total,
        items=[
            AdminAuditLogOut(
                id=record.id,
                actor_user_id=record.actor_user_id,
                actor_email=actor.email if actor else None,
                actor_display_name=actor.display_name if actor else None,
                actor_type=record.actor_type,
                action=record.action,
                target_type=record.target_type,
                target_id=record.target_id,
                metadata=record.metadata_json,
                created_at=record.created_at,
            )
            for record, actor in rows
        ],
    )


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserOut]:
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where((User.email.ilike(pattern)) | (User.display_name.ilike(pattern)))
    users = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return [AdminUserOut.model_validate(u, from_attributes=True) for u in users]


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminUserOut:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    user = await _get_user_or_404(user_id, db)
    user.platform_role = "platform_admin" if request.role == "admin" else "user"
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.user_role_changed",
        target_type="user",
        target_id=user.id,
        metadata={"platform_role": user.platform_role},
    )
    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user, from_attributes=True)


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
async def update_user_status(
    user_id: str,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminUserOut:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own status")
    user = await _get_user_or_404(user_id, db)
    user.is_active = request.is_active
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.user_status_changed",
        target_type="user",
        target_id=user.id,
        metadata={"is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user, from_attributes=True)

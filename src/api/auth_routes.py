from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.security import create_access_token, hash_password, verify_password
from src.config import get_settings
from src.db.models import User
from src.db.session import get_db
from src.models.auth_schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserPublic,
)
from src.services.workspace_service import create_personal_workspace

router = APIRouter()


def _to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        platform_role=user.platform_role,
        job_title=user.job_title,
        timezone=user.timezone,
        preferences=user.preferences,
    )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    normalized_email = str(request.email).lower()
    existing = (await db.execute(select(User).where(User.email == normalized_email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    settings = get_settings()
    initial_admin_email = settings.initial_admin_email.strip().lower()
    role = "admin" if initial_admin_email and normalized_email == initial_admin_email else "user"

    user = User(
        email=normalized_email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        role=role,
        platform_role="platform_admin" if role == "admin" else "user",
    )
    db.add(user)
    await db.flush()
    await create_personal_workspace(db, user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_to_public(user))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = (await db.execute(select(User).where(User.email == request.email.lower()))).scalar_one_or_none()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account has been disabled")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_to_public(user))


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return _to_public(current_user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    updates = request.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return _to_public(current_user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    current_user.password_hash = hash_password(request.new_password)
    await db.commit()

"""API routes for AI providers."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.jwt import get_user_id_from_token
from backend.core.providers.factory import ProviderFactory
from backend.core.providers.registry import provider_registry
from backend.database.connection import get_db_session
from backend.models.models import APIKey, ProviderConfig, ProviderType

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderConfigCreate(BaseModel):
    provider: ProviderType
    name: str = Field(..., min_length=1, max_length=100)
    config: dict = Field(default_factory=dict)
    models: list[str] = Field(default_factory=list)
    priority: int = 0


class ProviderConfigUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    is_enabled: bool | None = None
    config: dict | None = None
    models: list[str] | None = None
    priority: int | None = None


class ProviderConfigResponse(BaseModel):
    id: UUID
    provider: ProviderType
    name: str
    is_enabled: bool
    config: dict
    models: list[str]
    priority: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    provider: ProviderType
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)


class APIKeyResponse(BaseModel):
    id: UUID
    provider: ProviderType
    name: str
    is_active: bool
    created_at: str
    last_used: str | None

    class Config:
        from_attributes = True


class ProviderStatusResponse(BaseModel):
    provider: str
    connected: bool
    models: list[dict]


async def get_current_user_id(authorization: str = Header(None)) -> UUID:
    """Get current user ID from token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = (
        authorization.replace("Bearer ", "")
        if authorization.startswith("Bearer ")
        else authorization
    )
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return UUID(user_id)


@router.get("/", response_model=list[ProviderConfigResponse])
async def list_provider_configs(
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all provider configurations."""
    from sqlalchemy import select

    result = await db.execute(
        select(ProviderConfig).order_by(ProviderConfig.priority.desc())
    )
    configs = result.scalars().all()

    return [
        ProviderConfigResponse(
            id=c.id,
            provider=c.provider,
            name=c.name,
            is_enabled=c.is_enabled,
            config=c.config,
            models=c.models,
            priority=c.priority,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in configs
    ]


@router.post(
    "/", response_model=ProviderConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_provider_config(
    config_data: ProviderConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new provider configuration."""
    from sqlalchemy import select

    # Check if provider already configured
    existing = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == config_data.provider)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Provider {config_data.provider} already configured",
        )

    config = ProviderConfig(**config_data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return ProviderConfigResponse(
        id=config.id,
        provider=config.provider,
        name=config.name,
        is_enabled=config.is_enabled,
        config=config.config,
        models=config.models,
        priority=config.priority,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/{provider_id}", response_model=ProviderConfigResponse)
async def get_provider_config(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a provider configuration."""
    from sqlalchemy import select

    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Provider config not found")

    return ProviderConfigResponse(
        id=config.id,
        provider=config.provider,
        name=config.name,
        is_enabled=config.is_enabled,
        config=config.config,
        models=config.models,
        priority=config.priority,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.patch("/{provider_id}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider_id: UUID,
    config_data: ProviderConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update a provider configuration."""
    from sqlalchemy import select

    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Provider config not found")

    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)

    return ProviderConfigResponse(
        id=config.id,
        provider=config.provider,
        name=config.name,
        is_enabled=config.is_enabled,
        config=config.config,
        models=config.models,
        priority=config.priority,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_config(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a provider configuration."""
    from sqlalchemy import select

    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.id == provider_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Provider config not found")

    await db.delete(config)
    await db.commit()


@router.get("/status/all", response_model=list[ProviderStatusResponse])
async def get_all_provider_status(
    user_id: UUID = Depends(get_current_user_id),
):
    """Get connection status for all registered providers."""
    statuses = []

    for provider in provider_registry.list_all_providers():
        connected = await provider.validate_connection()
        models = provider_registry.get_cached_models(provider.provider_name)

        statuses.append(
            ProviderStatusResponse(
                provider=provider.provider_name,
                connected=connected,
                models=[
                    {
                        "id": m.id,
                        "name": m.name,
                        "capabilities": [c.value for c in m.capabilities],
                        "max_tokens": m.max_tokens,
                        "context_window": m.context_window,
                    }
                    for m in models
                ],
            )
        )

    return statuses


@router.post("/{provider_name}/test", response_model=ProviderStatusResponse)
async def test_provider_connection(
    provider_name: str,
    user_id: UUID = Depends(get_current_user_id),
):
    """Test a specific provider connection."""
    provider = provider_registry.get_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    connected = await provider.validate_connection()
    models = provider_registry.get_cached_models(provider_name)

    return ProviderStatusResponse(
        provider=provider_name,
        connected=connected,
        models=[
            {
                "id": m.id,
                "name": m.name,
                "capabilities": [c.value for c in m.capabilities],
                "max_tokens": m.max_tokens,
                "context_window": m.context_window,
            }
            for m in models
        ],
    )


@router.get("/supported/list")
async def list_supported_providers():
    """List all supported provider types."""
    return {"providers": ProviderFactory.get_supported_providers()}


# API Key endpoints
@router.get("/keys/", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """List user's API keys."""
    from sqlalchemy import select

    result = await db.execute(select(APIKey).where(APIKey.user_id == user_id))
    keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=k.id,
            provider=k.provider,
            name=k.name,
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
            last_used=k.last_used.isoformat() if k.last_used else None,
        )
        for k in keys
    ]


@router.post(
    "/keys/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Store an API key (encrypted in production)."""
    from sqlalchemy import select

    from backend.core.auth.jwt import get_password_hash

    # Check if key with same name exists for this provider
    existing = await db.execute(
        select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.provider == key_data.provider,
            APIKey.name == key_data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="API key with this name already exists"
        )

    # In production, encrypt the key
    encrypted_key = get_password_hash(key_data.api_key)

    api_key = APIKey(
        user_id=user_id,
        provider=key_data.provider,
        name=key_data.name,
        encrypted_key=encrypted_key,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse(
        id=api_key.id,
        provider=api_key.provider,
        name=api_key.name,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
        last_used=api_key.last_used.isoformat() if api_key.last_used else None,
    )


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete an API key."""
    from sqlalchemy import select

    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(api_key)
    await db.commit()

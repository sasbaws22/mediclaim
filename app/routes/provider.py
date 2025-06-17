from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID

from app.core.deps import get_db, AccessTokenBearer, get_current_active_user
from app.cruds.crud_provider import provider as crud_provider
from app.schemas.provider import ProviderCreate, ProviderRead, ProviderUpdate
from app.models.models import User, UserRole

router = APIRouter()
access_token_bearer = AccessTokenBearer()


@router.post("/", response_model=ProviderRead)
async def create_provider(
    *,
    db: AsyncSession = Depends(get_db),
    provider_in: ProviderCreate
) -> Any:
    """
    Register a new insurance provider
    """
    existing_provider = await crud_provider.get_by_email(db, email=provider_in.contact_email)
    if existing_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provider with this email already exists in the system.",
        )
    provider = await crud_provider.create(db, obj_in=provider_in)
    return provider

@router.get("/", response_model=List[ProviderRead])
async def read_providers(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """
    Retrieve all insurance providers.
    """
    providers = await crud_provider.get_multi(db, skip=skip, limit=limit)
    return providers

@router.get("/{provider_id}", response_model=ProviderRead)
async def read_provider_by_id(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific insurance provider by ID.
    """
    provider = await crud_provider.get(db, id=provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    return provider

@router.put("/{provider_id}", response_model=ProviderRead)
async def update_provider(
    provider_id: UUID,
    provider_in: ProviderUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update an insurance provider by ID.
    """
    provider = await crud_provider.get(db, id=provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    updated_provider = await crud_provider.update(db, db_obj=provider, obj_in=provider_in)
    return updated_provider

@router.delete("/{provider_id}", response_model=ProviderRead)
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete an insurance provider by ID.
    """
    provider = await crud_provider.get(db, id=provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    deleted_provider = await crud_provider.remove(db, id=provider_id)
    return deleted_provider



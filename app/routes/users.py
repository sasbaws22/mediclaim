from uuid import UUID
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core import deps 
from sqlmodel.ext.asyncio.session import AsyncSession 
from app.db.session import get_db
from app.cruds.crud_user import user as user_crud 
from app.cruds.base import CRUDBase
from app.models.models import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate,UserPatch

router = APIRouter()
base = CRUDBase(User)
@router.get("/me")
def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user
    """
    return current_user

@router.put("/me", response_model=UserSchema)
def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update current user
    """
    user = user_crud.update(db, db_obj=current_user, obj_in=user_in)
    return user

@router.get("")
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Retrieve users (admin only)
    """
    users = await base.get_multi(db, skip=skip, limit=limit)
    return users

@router.post("")
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Create new user (admin only)
    """
    user = user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        )
    user = await user_crud.create(db, obj_in=user_in)
    return user

@router.get("/{user_id}", response_model=UserSchema)
async def read_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Get a specific user by id (admin only)
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Update a user (admin only)
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user = user_crud.update(db, db_obj=user, obj_in=user_in)
    return user 

@router.patch("/{user_id}", response_model=UserSchema)
async def patch_user(  
    user_id: UUID,
    user_in:UserPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Any:
    """
    Update a user (admin only)
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user = await base.patch(db,db_obj=user,obj_in=user_in,id=user_id)
    return user

@router.delete("/{user_id}", response_model=UserSchema)
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: str,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Delete a user (admin only)
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user = user_crud.remove(db, id=user_id)
    return user

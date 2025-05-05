from typing import Any, Dict, Optional, Union, List
from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import status,HTTPException
from app.core.security import get_password_hash, verify_password
from app.cruds.base import CRUDBase
from app.models.models import User
from app.schemas.user import UserCreate, UserUpdate, UserPatch


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate,UserPatch]):
    async def get_by_email(self, db: AsyncSession,email: str) -> User | None:
      statement = select(User).filter(User.email == email)
      result = await db.execute(statement)
      user = result.scalars().first()
      return user

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            role=obj_in.role,
            is_active=True,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db, db_obj=db_obj, obj_in=update_data)  
    
    

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> User:
        user = await self.get_by_email(db, email=email)
        if user: 
            
            return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_admin(self, user: User) -> bool:
        return user.role == "ADMIN"

    async  def get_by_role(self, db: AsyncSession, *, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        return select(User).filter(User.role == role).offset(skip).limit(limit)


user = CRUDUser(User)

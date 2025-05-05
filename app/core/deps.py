from typing import Generator, Optional
from datetime import datetime, timedelta
import jwt
from sqlmodel import desc, select
from fastapi import Depends, HTTPException, status,Request
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import ValidationError

from app.db.session import get_db
from app.models.models import User
from app.core.config import settings
from app.core.security import verify_password,decode_token
from app.schemas.auth import TokenPayload
from app.cruds.crud_user import user as user_crud

class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        creds: HTTPAuthorizationCredentials = await super().__call__(request)
        token = creds.credentials

        token_data = decode_token(token)
        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        self.verify_token_data(token_data)
        return token_data

    def verify_token_data(self, token_data: dict) -> None:
        raise NotImplementedError("Please override this method in a child class")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh"):
            raise HTTPException(status_code=401, detail="Access token required")


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if not token_data.get("refresh"):
            raise HTTPException(status_code=401, detail="Refresh token required")



async def get_current_user(
    db: AsyncSession = Depends(get_db), token: dict = Depends(AccessTokenBearer())
) :
          email = token["user"]["email"]
          
          user = await user_crud.get_by_email(db,email)
          return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Validate that the current user is active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is an admin
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_hr_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is HR
    """
    if current_user.role != "HR" and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_cs_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is Customer Service
    """
    if current_user.role != "CUSTOMER_SERVICE" and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_claims_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is Claims
    """
    if current_user.role != "CLAIMS" and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_md_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is MD
    """
    if current_user.role != "MD" and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_finance_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is Finance
    """
    if current_user.role != "FINANCE" and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_user_by_email( user_email: str, db: AsyncSession):
             statement = select(User).where(User.email==user_email)
             result = await db.execute(statement)
             user = result.first()

             return user
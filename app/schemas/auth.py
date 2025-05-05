from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

from pydantic import BaseModel, Field


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


# Auth schemas
class Login(BaseModel):
    email: str
    password: str


class PasswordResetRequestModel(BaseModel):
    email: str


class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str
  
    class Config:
        from_attributes = True


import os
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str 
    ACCESS_TOKEN_EXPIRE_SECONDS: int 
    REFRESH_TOKEN_EXPIRE_DAYS: int 
    DOMAIN:str 
    ALLOWED_HOSTS:list 
    DATABASE_URL: str 
    ELASTICMAIL_API_KEY: str 
    ELASTICMAIL_FROM_EMAIL: EmailStr 
    ELASTICMAIL_FROM_NAME: str 
    ALGORITHM: str 
    API_V1_STR:str
    UPLOAD_DIRECTORY:str
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_SMS_NOTIFICATIONS: bool = True
    ENABLE_IN_APP_NOTIFICATIONS: bool = True
    
    class Config: 
        env_file = ".env"
        case_sensitive = True


settings = Settings()

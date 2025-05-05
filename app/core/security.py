import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union 
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import jwt
from passlib.context import CryptContext

from app.core.config import settings 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Token Generation
def create_access_token(
    user_data: dict,
    expiry: timedelta = None,
    refresh: bool = False
) -> str:
    """
    Create a JWT token with user data, optional expiry, and refresh flag.
    """
    payload = {
        "user": user_data,
        "exp": datetime.utcnow() + (expiry or timedelta(second=settings.ACCESS_TOKEN_EXPIRE_SECONDS)),
        "refresh": refresh
    }

    token = jwt.encode(payload, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


# JWT Token Decoding
def decode_token(token: str) -> dict | None:
    """
    Decode a JWT token and return payload if valid, else None.
    """
    try:
        token_data = jwt.decode(token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return token_data
    except jwt.PyJWTError as e:
        logging.exception("Failed to decode JWT token.")
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# URL-safe token serializer (for emails, etc.)
serializer = URLSafeTimedSerializer(
    secret_key=settings.SECRET_KEY,
    salt="email-configuration"
)

def create_url_safe_token(data: dict) -> str:
    """
    Create a URL-safe token for sending in links (e.g. email verification).
    """
    return serializer.dumps(data)

def decode_url_safe_token(token: str) -> dict | None:
    """
    Decode a URL-safe token. Returns the original data or None if invalid.
    """
    try:
        return serializer.loads(token)
    except (BadSignature, SignatureExpired) as e:
        logging.error(f"Invalid or expired URL-safe token: {e}")
        return None

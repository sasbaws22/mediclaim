from datetime import timedelta
from typing import Any
from sqlmodel import select
from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.core import deps 
from app.core.deps import AccessTokenBearer
from app.db.session import get_db 
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings
from app.core.security import get_password_hash,decode_url_safe_token,create_url_safe_token,create_access_token
from app.cruds.crud_user import user as user_crud
from app.models.models import User, AuditAction
from app.schemas.auth import Token, Login,PasswordResetConfirmModel,PasswordResetRequestModel
from app.schemas.user import User as UserSchema, UserCreate
from app.utils.audit import audit_service 
from app.core.config import Settings 
from app.utils.notification import NotificationService 



access_token_bearer = AccessTokenBearer()
send_notification_emails = NotificationService.send_email_notification 

router = APIRouter() 

@router.post("/login")
async def login_access_token(
    request: Request,
    form_data: Login,
    db: AsyncSession = Depends(get_db)
) -> Any:
 
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await user_crud.authenticate(
      db,  email=form_data.email, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    elif not user_crud.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
        )
    
    # Log successful login
    await  audit_service.log_login(
        db=db,
        user_id= user.id,
        ip_address=request.client.host if request.client else None,
        details={"email": user.email}
    )
    access_token_expires = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    refresh=False
    return {
        "access_token": create_access_token(
            user_data={"email":user.email,
                       "id":str(user.id)},
                        expiry= access_token_expires,
                        refresh=refresh                 
        ), 
        "user": {"id":user.id,
                 "email":user.email,
                 "full_name":user.full_name,
                 "is_active":user.is_active,
                 "role":user.role
                 },
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Refresh access token
    """
    access_token_expires = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    refresh=False
    return {
        "access_token": create_access_token(
            user_data={"email":current_user.email,
                       "id":str(current_user.id)}, 
                       expiry=access_token_expires,
                       refresh=refresh
        ),
        "token_type": "bearer",
    }

@router.post("/register")
async def register_user(
    request: Request,
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    Register a new user (policyholder)
    """
    user = await user_crud.get_by_email(db, email=user_in.email)
    if user == True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        ) 
    user = await user_crud.create(db, obj_in=user_in)
    
    # Log user creation
    await audit_service.log_create(
        db=db,
        user_id=user.id,
        entity_type="User",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
        details={"email": user.email, "role": user.role}
    ) 

    return user


@router.post("/password-reset-request")
async def password_reset_request(user_data: PasswordResetRequestModel,db:Session=Depends(get_db)):
     email = user_data.email
     
     token = create_url_safe_token({"email": email})
     print(email)

     link = f"https://{settings.DOMAIN}/api/v1/auth/password-reset-confirm/{token}"

     html_message = f"""
       <h1>Reset Your Password</h1>
       <p>Please click this <a href="{link}">link</a> to Reset Your Password</p>
        """
     subject = "Reset Your Password"

     await send_notification_emails( subject, html_message,[email],)
     return JSONResponse(
        content={
            "message": "Please check your email for instructions to reset your password",
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/password-reset-confirm/{token}")
async def reset_account_password(
    token: str,
    passwords: PasswordResetConfirmModel,
    db: AsyncSession = Depends(get_db)
):
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
        )

    token_data = decode_url_safe_token(token)

    user_email = token_data.get("email")

    if user_email:
        user = await  user_crud.get_by_email(db,email=user_email)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        passwd_hash = get_password_hash(new_password)
        user.hashed_password= passwd_hash
        await db.commit()

        return JSONResponse(
            content={"message": "Password reset Successfully"},
            status_code=status.HTTP_200_OK,
        )

    return JSONResponse(
        content={"message": "Error occured during password reset."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

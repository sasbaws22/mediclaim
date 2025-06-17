from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.core.deps import AccessTokenBearer, get_current_active_user
from app.models.models import User, UserRole
from app.cruds.crud_policyholder import policyholder
from app.schemas.policyholder import (
    PolicyholderProfileResponse,
    PolicyholderProfileUpdate,
    PolicyholderPolicyResponse,
    PolicyholderClaimCreate,
    PolicyholderClaimResponse,
    PolicyholderNotificationResponse,
    PolicyholderNotificationUpdate,
    PolicyholderDashboardResponse
)
from app.utils.audit import audit_service

router = APIRouter()
access_token_bearer = AccessTokenBearer()


async def get_current_policyholder(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Validate that the current user is a policyholder
    """
    if current_user.role != UserRole.POLICYHOLDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Policyholder role required."
        )
    return current_user


@router.get("/dashboard", response_model=PolicyholderDashboardResponse)
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get dashboard summary for the current policyholder
    """
    dashboard_data = await policyholder.get_dashboard_summary(db, user_id=current_user.id)
    
    # Log dashboard access
    
    return dashboard_data


@router.get("/profile", response_model=PolicyholderProfileResponse)
async def get_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get current policyholder's profile
    """
    profile = await policyholder.get_profile(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return profile


@router.put("/profile", response_model=PolicyholderProfileResponse)
async def update_profile(
    request: Request,
    profile_data: PolicyholderProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Update current policyholder's profile
    """
    updated_profile = await policyholder.update_profile(
        db, user_id=current_user.id, obj_in=profile_data
    )
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Log profile update
    await audit_service.log_update(
        db=db,
        user_id=current_user.id,
        entity_type="User",
        entity_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        details={"action": "profile_update", "updated_fields": list(profile_data.model_dump(exclude_unset=True).keys())}
    )
    
    return updated_profile


@router.get("/policies", response_model=List[PolicyholderPolicyResponse])
async def get_policies(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get all policies for the current policyholder
    """
    policies = await policyholder.get_policies(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    
    
    # Transform policies to include related data
    policy_responses = []
    for policy in policies:
        policy_response = PolicyholderPolicyResponse(
            id=policy.id,
            member_number=policy.member_number,
            plan_type=policy.plan_type,
            start_date=policy.start_date,
            end_date=policy.end_date,
            is_active=policy.is_active,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            employer_name=policy.employer.name if policy.employer else None,
            provider_name=policy.provider.name if policy.provider else None
        )
        policy_responses.append(policy_response)
    
    return policy_responses


@router.get("/policies/{policy_id}", response_model=PolicyholderPolicyResponse)
async def get_policy(
    request: Request,
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get a specific policy for the current policyholder
    """
    policy = await policyholder.get_policy_by_id(
        db, user_id=current_user.id, policy_id=policy_id
    )
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    return PolicyholderPolicyResponse(
        id=policy.id,
        member_number=policy.member_number,
        plan_type=policy.plan_type,
        start_date=policy.start_date,
        end_date=policy.end_date,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        employer_name=policy.employer.name if policy.employer else None,
        provider_name=policy.provider.name if policy.provider else None
    )


@router.get("/claims", response_model=List[PolicyholderClaimResponse])
async def get_claims(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get all claims for the current policyholder
    """
    claims = await policyholder.get_claims(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    
    # Transform claims to include related data
    claim_responses = []
    for claim in claims:
        claim_response = PolicyholderClaimResponse(
            id=claim.id,
            reference_number=claim.reference_number,
            policy_id=claim.policy_id,
            hospital_pharmacy=claim.hospital_pharmacy,
            reason=claim.reason,
            requested_amount=claim.requested_amount,
            approved_amount=claim.approved_amount,
            status=claim.status,
            submission_date=claim.submission_date,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            policy_member_number=claim.policies.member_number if claim.policies else None
        )
        claim_responses.append(claim_response)
    
    return claim_responses


@router.get("/claims/{claim_id}", response_model=PolicyholderClaimResponse)
async def get_claim(
    request: Request,
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get a specific claim for the current policyholder
    """
    claim = await policyholder.get_claim_by_id(
        db, user_id=current_user.id, claim_id=claim_id
    )
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    return PolicyholderClaimResponse(
        id=claim.id,
        reference_number=claim.reference_number,
        policy_id=claim.policy_id,
        hospital_pharmacy=claim.hospital_pharmacy,
        reason=claim.reason,
        requested_amount=claim.requested_amount,
        approved_amount=claim.approved_amount,
        status=claim.status,
        submission_date=claim.submission_date,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        policy_member_number=claim.policies.member_number if claim.policies else None
    )


@router.post("/claims", response_model=PolicyholderClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    request: Request,
    claim_data: PolicyholderClaimCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Create a new claim for the current policyholder
    """
    claim = await policyholder.create_claim(
        db, user_id=current_user.id, obj_in=claim_data
    )
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create claim. Policy not found or not accessible."
        )
    
    # Log claim creation
    await audit_service.log_create(
        db=db,
        user_id=current_user.id,
        entity_type="Claim",
        entity_id=claim.id,
        ip_address=request.client.host if request.client else None,
        details={
            "action": "claim_creation",
            "reference_number": claim.reference_number,
            "requested_amount": claim.requested_amount
        }
    )
    
    return PolicyholderClaimResponse(
        id=claim.id,
        reference_number=claim.reference_number,
        policy_id=claim.policy_id,
        hospital_pharmacy=claim.hospital_pharmacy,
        reason=claim.reason,
        requested_amount=claim.requested_amount,
        approved_amount=claim.approved_amount,
        status=claim.status,
        submission_date=claim.submission_date,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        policy_member_number=claim.policies.member_number if claim.policies else None
    )


@router.get("/notifications", response_model=List[PolicyholderNotificationResponse])
async def get_notifications(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Get all notifications for the current policyholder
    """
    notifications = await policyholder.get_notifications(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    
    # Transform notifications to include related data
    notification_responses = []
    for notification in notifications:
        notification_response = PolicyholderNotificationResponse(
            id=notification.id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type,
            is_read=notification.is_read,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
            claim_reference_number=notification.claim.reference_number if notification.claim else None
        )
        notification_responses.append(notification_response)
    
    return notification_responses


@router.put("/notifications/{notification_id}/read", response_model=PolicyholderNotificationResponse)
async def mark_notification_read(
    request: Request,
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_policyholder),
    _: dict = Depends(access_token_bearer)
):
    """
    Mark a notification as read for the current policyholder
    """
    notification = await policyholder.mark_notification_read(
        db, user_id=current_user.id, notification_id=notification_id
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Log notification update
    await audit_service.log_update(
        db=db,
        user_id=current_user.id,
        entity_type="Notification",
        entity_id=notification_id,
        ip_address=request.client.host if request.client else None,
        details={"action": "notification_mark_read"}
    )
    
    return PolicyholderNotificationResponse(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        is_read=notification.is_read,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
        claim_reference_number=notification.claim.reference_number if notification.claim else None
    )


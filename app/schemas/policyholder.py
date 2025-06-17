from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field


# Policyholder Profile Schemas
class PolicyholderProfileBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True


class PolicyholderProfileUpdate(PolicyholderProfileBase):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class PolicyholderProfileResponse(PolicyholderProfileBase):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Policyholder Policy Schemas
class PolicyholderPolicyResponse(BaseModel):
    id: UUID
    member_number: str
    plan_type: str
    start_date: datetime
    end_date: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
    employer_name: Optional[str] = None
    provider_name: Optional[str] = None

    class Config:
        from_attributes = True


# Policyholder Claim Schemas
class PolicyholderClaimCreate(BaseModel):
    policy_id: UUID
    hospital_pharmacy: str
    reason: str
    requested_amount: float


class PolicyholderClaimResponse(BaseModel):
    id: UUID
    reference_number: str
    policy_id: UUID
    hospital_pharmacy: str
    reason: str
    requested_amount: float
    approved_amount: Optional[float] = None
    status: str
    submission_date: datetime
    created_at: datetime
    updated_at: datetime
    policy_member_number: Optional[str] = None

    class Config:
        from_attributes = True


# Policyholder Notification Schemas
class PolicyholderNotificationResponse(BaseModel):
    id: UUID
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    updated_at: datetime
    claim_reference_number: Optional[str] = None

    class Config:
        from_attributes = True


class PolicyholderNotificationUpdate(BaseModel):
    is_read: bool = True


# Dashboard Summary Schema
class PolicyholderDashboardResponse(BaseModel):
    total_policies: int
    active_policies: int
    total_claims: int
    pending_claims: int
    approved_claims: int
    rejected_claims: int
    total_approved_amount: float
    unread_notifications: int

    class Config:
        from_attributes = True


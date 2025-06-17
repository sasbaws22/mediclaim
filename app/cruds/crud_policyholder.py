from typing import Any, Dict, Optional, Union, List
from uuid import UUID
from sqlmodel import select, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status
from app.cruds.base import CRUDBase
from app.models.models import User, Policy, Claim, Notification, UserRole, ClaimStatus
from app.schemas.policyholder import (
    PolicyholderProfileUpdate,
    PolicyholderClaimCreate,
    PolicyholderNotificationUpdate,
    PolicyholderDashboardResponse
)


class CRUDPolicyholder(CRUDBase[User, None, PolicyholderProfileUpdate, None]):
    
    async def get_profile(self, db: AsyncSession, *, user_id: UUID) -> User | None:
        """Get policyholder profile by user ID"""
        statement = select(User).where(
            and_(User.id == user_id, User.role == UserRole.POLICYHOLDER)
        )
        result = await db.exec(statement)
        return result.first()
    
    async def update_profile(
        self, db: AsyncSession, *, user_id: UUID, obj_in: PolicyholderProfileUpdate
    ) -> User | None:
        """Update policyholder profile"""
        user = await self.get_profile(db, user_id=user_id)
        if not user:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        return user
    
    async def get_policies(
        self, db: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Policy]:
        """Get all policies for a policyholder"""
        statement = (
            select(Policy)
            .where(Policy.policyholder_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.exec(statement)
        return result.all()
    
    async def get_policy_by_id(
        self, db: AsyncSession, *, user_id: UUID, policy_id: UUID
    ) -> Policy | None:
        """Get a specific policy for a policyholder"""
        statement = select(Policy).where(
            and_(Policy.id == policy_id, Policy.policyholder_id == user_id)
        )
        result = await db.exec(statement)
        return result.first()
    
    async def get_claims(
        self, db: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Claim]:
        """Get all claims for a policyholder"""
        statement = (
            select(Claim)
            .join(Policy, Claim.policy_id == Policy.id)
            .where(Policy.policyholder_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.exec(statement)
        return result.all()
    
    async def get_claim_by_id(
        self, db: AsyncSession, *, user_id: UUID, claim_id: UUID
    ) -> Claim | None:
        """Get a specific claim for a policyholder"""
        statement = (
            select(Claim)
            .join(Policy, Claim.policy_id == Policy.id)
            .where(and_(Claim.id == claim_id, Policy.policyholder_id == user_id))
        )
        result = await db.exec(statement)
        return result.first()
    
    async def create_claim(
        self, db: AsyncSession, *, user_id: UUID, obj_in: PolicyholderClaimCreate
    ) -> Claim | None:
        """Create a new claim for a policyholder"""
        # Verify the policy belongs to the user
        policy = await self.get_policy_by_id(db, user_id=user_id, policy_id=obj_in.policy_id)
        if not policy:
            return None
        
        # Generate unique reference number
        import uuid
        reference_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        
        claim = Claim(
            reference_number=reference_number,
            policy_id=obj_in.policy_id,
            hospital_pharmacy=obj_in.hospital_pharmacy,
            reason=obj_in.reason,
            requested_amount=obj_in.requested_amount,
            status=ClaimStatus.SUBMITTED
        )
        
        db.add(claim)
        await db.commit()
        await db.refresh(claim)
        return claim
    
    async def get_notifications(
        self, db: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Notification]:
        """Get all notifications for a policyholder"""
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.exec(statement)
        return result.all()
    
    async def mark_notification_read(
        self, db: AsyncSession, *, user_id: UUID, notification_id: UUID
    ) -> Notification | None:
        """Mark a notification as read"""
        statement = select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        )
        result = await db.exec(statement)
        notification = result.first()
        
        if not notification:
            return None
        
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification
    
    async def get_dashboard_summary(
        self, db: AsyncSession, *, user_id: UUID
    ) -> PolicyholderDashboardResponse:
        """Get dashboard summary for a policyholder"""
        # Get policies count
        policies_statement = select(Policy).where(Policy.policyholder_id == user_id)
        policies_result = await db.exec(policies_statement)
        policies = policies_result.all()
        
        total_policies = len(policies)
        active_policies = len([p for p in policies if p.is_active])
        
        # Get claims statistics
        claims_statement = (
            select(Claim)
            .join(Policy, Claim.policy_id == Policy.id)
            .where(Policy.policyholder_id == user_id)
        )
        claims_result = await db.exec(claims_statement)
        claims = claims_result.all()
        
        total_claims = len(claims)
        pending_claims = len([c for c in claims if c.status in [
            ClaimStatus.SUBMITTED, ClaimStatus.UNDER_REVIEW_CS, 
            ClaimStatus.UNDER_REVIEW_CLAIMS, ClaimStatus.PENDING_MD_APPROVAL
        ]])
        approved_claims = len([c for c in claims if c.status in [
            ClaimStatus.APPROVED, ClaimStatus.PARTIALLY_APPROVED, ClaimStatus.PAID
        ]])
        rejected_claims = len([c for c in claims if c.status == ClaimStatus.REJECTED])
        
        total_approved_amount = sum([
            c.approved_amount or 0 for c in claims 
            if c.approved_amount and c.status in [
                ClaimStatus.APPROVED, ClaimStatus.PARTIALLY_APPROVED, ClaimStatus.PAID
            ]
        ])
        
        # Get unread notifications count
        notifications_statement = select(Notification).where(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        )
        notifications_result = await db.exec(notifications_statement)
        unread_notifications = len(notifications_result.all())
        
        return PolicyholderDashboardResponse(
            total_policies=total_policies,
            active_policies=active_policies,
            total_claims=total_claims,
            pending_claims=pending_claims,
            approved_claims=approved_claims,
            rejected_claims=rejected_claims,
            total_approved_amount=total_approved_amount,
            unread_notifications=unread_notifications
        )


policyholder = CRUDPolicyholder(User)


from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form 
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid
import os

from app.core import deps 
from app.db.session import get_db
from app.models.models import User, Claim, ClaimStatus, UserRole,Policy,ClaimAttachment,ReviewItem,Review,Payment,Employer
from app.cruds.crud_user import user as user_crud
from app.utils.notification import notification_service
from app.core.config import settings 
from app.core.deps import AccessTokenBearer 
from app.cruds.base import CRUDBase
from app.schemas.claim import ClaimPatch,ClaimCreate,ClaimResponse,AttachmentPatch


access_token_bearer = AccessTokenBearer(auto_error=True)
base = CRUDBase(Claim) 
bases = CRUDBase(ClaimAttachment)
router = APIRouter()

@router.get("", response_model=List[dict])
async def get_claims(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Get list of claims based on user role
    """
    query = select(Claim)

    
    if status:
        query = query.filter(Claim.status == status)
    
    result = await db.execute(query.offset(skip).limit(limit))
    claims = result.scalars().all()

    response = []
    for claim in claims:
        response.append({
            "id": claim.id,
            "reference_number": claim.reference_number,
            "hospital_pharmacy": claim.hospital_pharmacy,
            "reason": claim.reason,
            "requested_amount": claim.requested_amount,
            "approved_amount": claim.approved_amount,
            "status": claim.status,
            "submission_date": claim.submission_date,
            "policy_id": claim.policy_id,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
        })
    
    return response


@router.post("", response_model=dict)
async def create_claim(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    policy_id: str = Form(...),
    hospital_pharmacy: str = Form(...),
    reason: str = Form(...),
    requested_amount: float = Form(...),
    attachments: List[UploadFile] = File(None),
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Create a new claim
    """
    # Fetch policy
    policy_stmt = select(Policy).where(Policy.id == policy_id)
    result = await db.execute(policy_stmt)
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    
    
    
    # Generate unique reference number
    reference_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    
    # Create claim
    claim = Claim(
        reference_number=reference_number,
        policy_id=policy_id,
        hospital_pharmacy=hospital_pharmacy,
        reason=reason,
        requested_amount=requested_amount,
        status=ClaimStatus.SUBMITTED,
    )
    
    db.add(claim)
    await db.flush()  # To get claim.id populated before attachments
    
    # Save attachments if provided
    if attachments:
        os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
        
        for attachment in attachments:
            filename = f"{uuid.uuid4()}{os.path.splitext(attachment.filename)[1]}"
            filepath = os.path.join(settings.UPLOAD_DIRECTORY, filename)
            
            with open(filepath, "wb") as f:
                f.write(await attachment.read())
            
            claim_attachment = ClaimAttachment(
                claim_id=claim.id,
                file_name=attachment.filename,
                file_path=filepath,
                file_type=attachment.content_type,
            )
            db.add(claim_attachment)
    
    await db.commit()
    await db.refresh(claim)
    
    # Fetch users for notification
    policyholder_stmt = select(User).where(User.id == policy.policyholder_id)
    result = await db.execute(policyholder_stmt)
    policyholder = result.scalar_one_or_none()

    hr_users = await user_crud.get_by_role(db, role=UserRole.HR)
    cs_users = await user_crud.get_by_role(db, role=UserRole.CUSTOMER_SERVICE)
    
    await notification_service.notify_claim_submission(
        background_tasks=background_tasks,
        db=db,
        claim=claim,
        policyholder=policyholder,
        hr_users=hr_users,
        cs_users=cs_users,
    )
    
    return {
        "id": claim.id,
        "reference_number": claim.reference_number,
        "status": claim.status,
        "message": "Claim submitted successfully",
    }



@router.get("/{claim_id}", response_model=dict)
async def get_claim(
    claim_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Get claim by ID
    """
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    # Check permissions
    result = await db.execute(select(Policy).where(Policy.id == claim.policy_id))
    policy = result.scalar_one_or_none()
   

    # Get attachments
    result = await db.execute(select(ClaimAttachment).where(ClaimAttachment.claim_id == claim.id))
    attachments = result.scalars().all()
    attachment_list = [
        {
            "id": a.id,
            "file_name": a.file_name,
            "file_type": a.file_type,
            "uploaded_at": a.uploaded_at,
        }
        for a in attachments
    ]

    # Get reviews and review items
    result = await db.execute(select(Review).where(Review.claim_id == claim.id))
    reviews = result.scalars().all()
    review_list = []
    for review in reviews:
        result = await db.execute(select(ReviewItem).where(ReviewItem.review_id == review.id))
        items = result.scalars().all()
        item_list = [
            {
                "id": item.id,
                "item_name": item.item_name,
                "requested_amount": item.requested_amount,
                "approved_amount": item.approved_amount,
                "status": item.status,
                "rejection_reason": item.rejection_reason,
            }
            for item in items
        ]

        result = await db.execute(select(User).where(User.id == review.reviewer_id))
        reviewer = result.scalar_one_or_none()
        reviewer_name = reviewer.full_name if reviewer else "Unknown"

        review_list.append({
            "id": review.id,
            "review_type": review.review_type,
            "reviewer_name": reviewer_name,
            "comments": review.comments,
            "decision": review.decision,
            "rejection_reason": review.rejection_reason,
            "reviewed_at": review.reviewed_at,
            "items": item_list
        })

    # Get payments
    result = await db.execute(select(Payment).where(Payment.claim_id == claim.id))
    payments = result.scalars().all()
    payment_list = []
    for payment in payments:
        result = await db.execute(select(User).where(User.id == payment.processed_by_id))
        processor = result.scalar_one_or_none()
        processor_name = processor.full_name if processor else "Unknown"

        payment_list.append({
            "id": payment.id,
            "invoice_number": payment.invoice_number,
            "payment_amount": payment.payment_amount,
            "payment_date": payment.payment_date,
            "payment_status": payment.payment_status,
            "processor_name": processor_name,
            "created_at": payment.created_at
        })

    # Get policyholder and employer
    result = await db.execute(select(User).where(User.id == policy.policyholder_id))
    policyholder = result.scalar_one_or_none()
    result = await db.execute(select(Employer).where(Employer.id == policy.employer_id))
    employer = result.scalar_one_or_none()

    return {
        "id": claim.id,
        "reference_number": claim.reference_number,
        "hospital_pharmacy": claim.hospital_pharmacy,
        "reason": claim.reason,
        "requested_amount": claim.requested_amount,
        "approved_amount": claim.approved_amount,
        "status": claim.status,
        "submission_date": claim.submission_date,
        "created_at": claim.created_at,
        "updated_at": claim.updated_at,
        "policy": {
            "id": policy.id,
            "member_number": policy.member_number,
            "plan_type": policy.plan_type,
        },
        "policyholder": {
            "id": policyholder.id,
            "full_name": policyholder.full_name,
            "email": policyholder.email,
        },
        "employer": {
            "id": employer.id,
            "name": employer.name,
        },
        "attachments": attachment_list,
        "reviews": review_list,
        "payments": payment_list,
    }



@router.put("/{claim_id}/status", response_model=dict)
async def update_claim_status(
    claim_id: UUID,
    background_tasks: BackgroundTasks,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Update claim status
    """
    # Check if status is valid
    if status not in [s for s in dir(ClaimStatus) if not s.startswith("__")]:
        return {"detail":"Invalid status"}

    # Fetch the claim
    result = await db.execute(select(Claim).filter(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        return {"detail":"Claim not found"}

    

    # Update claim status
    claim.status = status
    db.commit()
    db.refresh(claim)

    # Fetch policy and policyholder
    result = await db.execute(select(Policy).filter(Policy.id == claim.policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise {"detail":"Policy not found"}

    result = await db.execute(select(User).filter(User.id == policy.policyholder_id))
    policyholder = result.scalar_one_or_none()

    # Send notification
    await notification_service.notify_claim_status_update(
        background_tasks=background_tasks,
        db=db,
        claim=claim,
        policyholder=policyholder,
        new_status=status
    )

    return {
        "id": claim.id,
        "reference_number": claim.reference_number,
        "status": claim.status,
        "message": "Claim status updated successfully"
    }

from fastapi import UploadFile, File, HTTPException, status
from sqlalchemy.future import select
import os
import uuid

@router.post("/{claim_id}/attachments", response_model=dict)
async def upload_attachment(
    claim_id: UUID,
    attachment: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
_: dict = Depends(access_token_bearer)
) -> Any:
    """
    Upload attachment for a claim
    """
    # Fetch claim
    result = await db.execute(select(Claim).filter(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)

    # Generate unique filename
    filename = f"{uuid.uuid4()}{os.path.splitext(attachment.filename)[1]}"
    filepath = os.path.join(settings.UPLOAD_DIRECTORY, filename)

    # Save file to disk
    with open(filepath, "wb") as f:
        f.write(await attachment.read())

    # Save attachment record
    claim_attachment = ClaimAttachment(
        claim_id=claim_id,
        file_name=attachment.filename,
        file_path=filepath,
        file_type=attachment.content_type,
    )
    db.add(claim_attachment)
    await db.commit()
    await db.refresh(claim_attachment)

    return {
        "id": claim_attachment.id,
        "file_name": claim_attachment.file_name,
        "file_type": claim_attachment.file_type,
        "uploaded_at": claim_attachment.uploaded_at,
        "message": "Attachment uploaded successfully"
    }

@router.delete("/{claim_id}/attachments/{attachment_id}", response_model=dict)
async def delete_attachment(
    claim_id: UUID,
    attachment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Delete attachment
    """
    # Fetch claim
    result = await db.execute(select(Claim).filter(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )


    # Fetch attachment
    result = await db.execute(
        select(ClaimAttachment).filter(
            ClaimAttachment.id == attachment_id,
            ClaimAttachment.claim_id == claim_id,
        )
    )
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    # Delete file if exists
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    # Delete record
    await db.delete(attachment)
    await db.commit()

    return {
        "message": "Attachment deleted successfully"
    }

@router.patch("/{claim_id}")
async def patch_claim(  
    claim_id: UUID,
    claim_in: ClaimPatch,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(access_token_bearer)
) -> Any:
   
    statement = select(Claim).where(Claim.id== claim_id)
    result = await db.exec(statement) 
    claim = result.first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    claim = await base.patch(db,db_obj=claim,obj_in=claim_in,id=claim_id)
    return claim 

@router.patch("/{claim_id}/attachments/{attachment_id}")
async def patch_attachment(  
    attachment_id: UUID,
    attachment_in: AttachmentPatch,
    db: AsyncSession = Depends(get_db), 
    _: dict = Depends(access_token_bearer)
) -> Any:
   
    statement = select(ClaimAttachment).where(ClaimAttachment.id== attachment_id)
    result = await db.exec(statement) 
    attachment = result.first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    attachment = await bases.patch(db,db_obj=ClaimAttachment,obj_in=attachment_in,id=attachment_id)
    return attachment
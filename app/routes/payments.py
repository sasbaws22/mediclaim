from typing import Any, List, Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Form
from sqlmodel.ext.asyncio.session import AsyncSession 
from app.db.session import get_db 
from sqlmodel import select
from app.core import deps
from app.models.models import User, Claim, Payment, PaymentStatus, ClaimStatus, UserRole,Policy
from app.utils.notification import notification_service

router = APIRouter()


@router.get("", response_model=List[dict])
async def get_payments(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    claim_id: Optional[UUID] = None,
    payment_status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get list of payments
    """
    query = select(Payment)

    if claim_id:
        query = query.filter(Payment.claim_id == claim_id)

    if payment_status:
        query = query.filter(Payment.payment_status == payment_status)

    if current_user.role == UserRole.POLICYHOLDER:
        # Policyholders can only see payments for their own claims
        query = query.join(Payment.claim).join(Claim.policy).filter(Policy.policyholder_id == current_user.id)
    elif current_user.role not in [UserRole.FINANCE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    payments = result.scalars().all()

    payment_list = []
    for payment in payments:
        # Get processor name
        processor = None
        if payment.processed_by_id:
            processor_result = await db.execute(select(User).where(User.id == payment.processed_by_id))
            processor = processor_result.scalar_one_or_none()
        processor_name = processor.full_name if processor else "Unknown"

        # Get claim reference number
        claim_result = await db.execute(select(Claim).where(Claim.id == payment.claim_id))
        claim = claim_result.scalar_one_or_none()
        claim_reference = claim.reference_number if claim else "Unknown"

        payment_list.append({
            "id": payment.id,
            "claim_id": payment.claim_id,
            "claim_reference": claim_reference,
            "invoice_number": payment.invoice_number,
            "payment_amount": payment.payment_amount,
            "payment_date": payment.payment_date,
            "payment_status": payment.payment_status,
            "processed_by_id": payment.processed_by_id,
            "processor_name": processor_name,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        })

    return payment_list

@router.post("/claims/{claim_id}/payments", response_model=dict)
async def create_payment(
    claim_id: UUID,
    background_tasks: BackgroundTasks,
    invoice_number: str = Form(...),
    payment_amount: float = Form(...),
    payment_date: date = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_finance_user),
) -> Any:
    """
    Create a new payment for a claim
    """
    # Check if claim exists
    result = await db.execute(select(Claim).filter(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    # Check if claim is approved or partially approved
    if claim.status not in [ClaimStatus.APPROVED, ClaimStatus.PARTIALLY_APPROVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim must be approved or partially approved to create payment",
        )

    # Create payment
    payment = Payment(
        claim_id=claim_id,
        invoice_number=invoice_number,
        payment_amount=payment_amount,
        payment_date=payment_date,
        payment_status=PaymentStatus.SCHEDULED,
        processed_by_id=current_user.id,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    # Update claim status
    claim.status = ClaimStatus.PENDING_PAYMENT
    await db.commit()
    await db.refresh(claim)

    # Fetch policy
    result = await db.execute(select(Policy).filter(Policy.id == claim.policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    # Fetch policyholder
    result = await db.execute(select(User).filter(User.id == policy.policyholder_id))
    policyholder = result.scalar_one_or_none()
    if not policyholder:
        raise HTTPException(status_code=404, detail="Policyholder not found.")

    # Send notification
    await notification_service.notify_payment_scheduled(
        background_tasks=background_tasks,
        db=db,
        claim=claim,
        policyholder=policyholder,
        payment_amount=payment_amount,
        payment_date=payment_date.strftime("%Y-%m-%d")
    )

    return {
        "id": payment.id,
        "claim_id": payment.claim_id,
        "invoice_number": payment.invoice_number,
        "payment_amount": payment.payment_amount,
        "payment_date": payment.payment_date,
        "payment_status": payment.payment_status,
        "message": "Payment scheduled successfully"
    }

@router.get("/{payment_id}", response_model=dict)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get payment by ID
    """
    # Fetch payment
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    
    # Check permissions
    if current_user.role == UserRole.POLICYHOLDER:
        # Get the claim and policy
        claim_result = await db.execute(select(Claim).where(Claim.id == payment.claim_id))
        claim = claim_result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated claim not found",
            )
        
        policy_result = await db.execute(select(Policy).where(Policy.id == claim.policy_id))
        policy = policy_result.scalar_one_or_none()
        
        if not policy or policy.policyholder_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
    
    elif current_user.role not in [UserRole.FINANCE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Fetch processor
    processor_name = "Unknown"
    if payment.processed_by_id:
        processor_result = await db.execute(select(User).where(User.id == payment.processed_by_id))
        processor = processor_result.scalar_one_or_none()
        if processor:
            processor_name = processor.full_name

    # Fetch claim for claim reference
    claim_reference = "Unknown"
    policyholder_name = "Unknown"
    if payment.claim_id:
        claim_result = await db.execute(select(Claim).where(Claim.id == payment.claim_id))
        claim = claim_result.scalar_one_or_none()
        
        if claim:
            claim_reference = claim.reference_number

            # Fetch policy and policyholder
            policy_result = await db.execute(select(Policy).where(Policy.id == claim.policy_id))
            policy = policy_result.scalar_one_or_none()
            if policy:
                policyholder_result = await db.execute(select(User).where(User.id == policy.policyholder_id))
                policyholder = policyholder_result.scalar_one_or_none()
                if policyholder:
                    policyholder_name = policyholder.full_name

    result = {
        "id": payment.id,
        "claim_id": payment.claim_id,
        "claim_reference": claim_reference,
        "invoice_number": payment.invoice_number,
        "payment_amount": payment.payment_amount,
        "payment_date": payment.payment_date,
        "payment_status": payment.payment_status,
        "processed_by_id": payment.processed_by_id,
        "processor_name": processor_name,
        "policyholder_name": policyholder_name,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at
    }

    return result


@router.put("/{payment_id}", response_model=dict)
async def update_payment(
    payment_id: UUID,
    background_tasks: BackgroundTasks,
    invoice_number: Optional[str] = Form(None),
    payment_amount: Optional[float] = Form(None),
    payment_date: Optional[date] = Form(None),
    payment_status: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_finance_user),
) -> Any:
    """
    Update payment by ID
    """

    # Ensure finance user
    if current_user.role != UserRole.FINANCE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Get the payment
    result = await db.execute(select(Payment).filter(Payment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Validate payment status
    if payment_status and payment_status not in [
        PaymentStatus.SCHEDULED, PaymentStatus.PROCESSED, PaymentStatus.FAILED
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment status",
        )

    # Update payment fields
    if invoice_number:
        payment.invoice_number = invoice_number
    if payment_amount is not None:
        payment.payment_amount = payment_amount
    if payment_date:
        payment.payment_date = payment_date
    if payment_status:
        payment.payment_status = payment_status

    await db.commit()
    await db.refresh(payment)

    # Update claim if necessary
    if payment_status:
        result = await db.execute(select(Claim).filter(Claim.id == payment.claim_id))
        claim = result.scalar_one_or_none()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        if payment_status == PaymentStatus.PROCESSED:
            claim.status = ClaimStatus.PAID
            await db.commit()
            await db.refresh(claim)

            # Notify policyholder
            result = await db.execute(select(Policy).filter(Policy.id == claim.policy_id))
            policy = result.scalar_one_or_none()

            result = await db.execute(select(User).filter(User.id == policy.policyholder_id))
            policyholder = result.scalar_one_or_none()

            await notification_service.notify_claim_status_update(
                background_tasks=background_tasks,
                db=db,
                claim=claim,
                policyholder=policyholder,
                new_status=ClaimStatus.PAID
            )

    return {
        "id": payment.id,
        "invoice_number": payment.invoice_number,
        "payment_amount": payment.payment_amount,
        "payment_date": payment.payment_date,
        "payment_status": payment.payment_status,
        "message": "Payment updated successfully"
    }

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core import deps 
from app.db.session import get_db 
from sqlmodel import select 
from app.core.deps import AccessTokenBearer
from app.models.models import User, Claim, Review, ReviewType, ReviewDecision, ReviewItem, ReviewItemStatus, UserRole,ClaimStatus,Policy 
from app.schemas.review import ReviewCreate,ReviewPatch,ReviewResponse 
from app.cruds.base import CRUDBase

router = APIRouter()
access_token_bearer = AccessTokenBearer()  
base = CRUDBase(Review)

@router.get("", response_model=List[dict])
async def get_reviews(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    claim_id: Optional[UUID] = None,
    review_type: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user), 
    _: dict = Depends(access_token_bearer)
) -> Any:

    # Build query
    query = select(Review)

    if claim_id:
        query = query.where(Review.claim_id == claim_id)

    if review_type:
        query = query.where(Review.review_type == review_type)

    # Role-based filtering
    if current_user.role != UserRole.ADMIN:
        if current_user.role == UserRole.CUSTOMER_SERVICE:
            query = query.where(Review.review_type == ReviewType.CUSTOMER_SERVICE)
        elif current_user.role == UserRole.CLAIMS:
            query = query.where(Review.review_type == ReviewType.CLAIMS)
        elif current_user.role == UserRole.MD:
            query = query.where(Review.review_type == ReviewType.MD)
        elif current_user.role == UserRole.POLICYHOLDER:
            query = query.join(Review.claim).join(Claim.policy).where(
                Claim.policy.has(policyholder_id=current_user.id)
            )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    # Build response
    response = []
    for review in reviews:
        # Get reviewer name
        reviewer_result = await db.execute(select(User).where(User.id == review.reviewer_id))
        reviewer = reviewer_result.scalar_one_or_none()
        reviewer_name = reviewer.full_name if reviewer else "Unknown"

        # Get review items
        item_result = await db.execute(select(ReviewItem).where(ReviewItem.review_id == review.id))
        items = item_result.scalars().all()
        item_dicts = [
            {
                "id": item.id,
                "item_name": item.item_name,
                "requested_amount": item.requested_amount,
                "approved_amount": item.approved_amount,
                "status": item.status,
                "rejection_reason": item.rejection_reason
            } for item in items
        ]

        response.append({
            "id": review.id,
            "claim_id": review.claim_id,
            "reviewer_id": review.reviewer_id,
            "reviewer_name": reviewer_name,
            "review_type": review.review_type,
            "comments": review.comments,
            "decision": review.decision,
            "rejection_reason": review.rejection_reason,
            "reviewed_at": review.reviewed_at,
            "items": item_dicts
        })

    return response


@router.post("/claims/{claim_id}/reviews", response_model=dict)
async def create_review(
    claim_id: UUID,
    review_type: str = Form(...),
    comments: str = Form(...),
    decision: str = Form(...),
    rejection_reason: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user), 
     _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Create a new review for a claim
    """
    # Fetch claim
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    # Validate review type
    if review_type not in [ReviewType.CUSTOMER_SERVICE, ReviewType.CLAIMS, ReviewType.MD]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review type",
        )
    
    # Validate decision
    if decision not in [ReviewDecision.APPROVED, ReviewDecision.PARTIALLY_APPROVED, 
                        ReviewDecision.REJECTED, ReviewDecision.NEEDS_MORE_INFO]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision",
        )
    
    # Check permissions based on role
    if (current_user.role == UserRole.CUSTOMER_SERVICE and review_type != ReviewType.CUSTOMER_SERVICE) or \
       (current_user.role == UserRole.CLAIMS and review_type != ReviewType.CLAIMS) or \
       (current_user.role == UserRole.MD and review_type != ReviewType.MD) or \
       current_user.role in [UserRole.POLICYHOLDER, UserRole.HR, UserRole.FINANCE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Create the review
    review = Review(
        claim_id=claim_id,
        reviewer_id=current_user.id,
        review_type=review_type,
        comments=comments,
        decision=decision,
        rejection_reason=rejection_reason,
    )
    
    db.add(review)

    # Update claim status based on review
    if review_type == ReviewType.CUSTOMER_SERVICE:
        if decision in [ReviewDecision.APPROVED, ReviewDecision.PARTIALLY_APPROVED]:
            claim.status = ClaimStatus.UNDER_REVIEW_CLAIMS
        elif decision == ReviewDecision.REJECTED:
            claim.status = ClaimStatus.REJECTED

    elif review_type == ReviewType.CLAIMS:
        if decision in [ReviewDecision.APPROVED, ReviewDecision.PARTIALLY_APPROVED]:
            claim.status = ClaimStatus.PENDING_MD_APPROVAL
        elif decision == ReviewDecision.REJECTED:
            claim.status = ClaimStatus.REJECTED

        elif decision == ReviewDecision.REJECTED:
            claim.status = ClaimStatus.REJECTED
    
        await db.commit()
        await db.refresh(review)

        return {
        "id": review.id,
        "claim_id": review.claim_id,
        "review_type": review.review_type,
        "decision": review.decision,
        "message": "Review created successfully"
    }

@router.get("/{review_id}", response_model=dict)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db), 
     _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Get review by ID
    """
    # Fetch the review
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Permission checks
    # if current_user.role == UserRole.POLICYHOLDER:
    #     claim_result = await db.execute(select(Claim).where(Claim.id == review.claim_id))
    #     claim = claim_result.scalar_one_or_none()
    #     if not claim:
    #         raise HTTPException(status_code=404, detail="Claim not found")

    #     policy_result = await db.execute(select(Policy).where(Policy.id == claim.policy_id))
    #     policy = policy_result.scalar_one_or_none()
    #     if not policy or policy.policyholder_id != current_user.id:
    #         raise HTTPException(status_code=403, detail="Not enough permissions")

    # elif current_user.role == UserRole.CUSTOMER_SERVICE and review.review_type != ReviewType.CUSTOMER_SERVICE:
    #     raise HTTPException(status_code=403, detail="Not enough permissions")

    # elif current_user.role == UserRole.CLAIMS and review.review_type != ReviewType.CLAIMS:
    #     raise HTTPException(status_code=403, detail="Not enough permissions")

    # elif current_user.role == UserRole.MD and review.review_type != ReviewType.MD:
    #     raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get reviewer
    reviewer_result = await db.execute(select(User).where(User.id == review.reviewer_id))
    reviewer = reviewer_result.scalar_one_or_none()
    reviewer_name = reviewer.full_name if reviewer else "Unknown"

    # Get review items
    item_result = await db.execute(select(ReviewItem).where(ReviewItem.review_id == review.id))
    items = item_result.scalars().all()
    item_dicts = [
        {
            "id": item.id,
            "item_name": item.item_name,
            "requested_amount": item.requested_amount,
            "approved_amount": item.approved_amount,
            "status": item.status,
            "rejection_reason": item.rejection_reason
        }
        for item in items
    ]

    # Return combined data
    return {
        "id": review.id,
        "claim_id": review.claim_id,
        "reviewer_id": review.reviewer_id,
        "reviewer_name": reviewer_name,
        "review_type": review.review_type,
        "comments": review.comments,
        "decision": review.decision,
        "rejection_reason": review.rejection_reason,
        "reviewed_at": review.reviewed_at,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "items": item_dicts,
    }

@router.put("/{review_id}", response_model=dict)
async def update_review(
    review_id: UUID,
    comments: Optional[str] = Form(None),
    decision: Optional[str] = Form(None),
    rejection_reason: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db), 
     _: dict = Depends(access_token_bearer)
) -> Any:
  
    # Fetch the review instance
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    

    # Validate decision if provided
    if decision and decision not in [
        ReviewDecision.APPROVED,
        ReviewDecision.PARTIALLY_APPROVED,
        ReviewDecision.REJECTED,
        ReviewDecision.NEEDS_MORE_INFO
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision",
        )

    # Apply updates
    if comments is not None:
        review.comments = comments
    if decision is not None:
        review.decision = decision
    if rejection_reason is not None:
        review.rejection_reason = rejection_reason

    await db.commit()
    await db.refresh(review)

    return {
        "id": review.id,
        "claim_id": review.claim_id,
        "review_type": review.review_type,
        "decision": review.decision,
        "message": "Review updated successfully"
    }


@router.post("/{review_id}/items", response_model=dict)
async def add_review_item(
    review_id: UUID,
    item_name: str = Form(...),
    requested_amount: float = Form(...),
    approved_amount: float = Form(...),
    status: str = Form(...),
    rejection_reason: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db), 
     _: dict = Depends(access_token_bearer)
) -> Any:
   
    # Fetch review
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")


    # Validate status
    if status not in [ReviewItemStatus.APPROVED, ReviewItemStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Create review item
    review_item = ReviewItem(
        review_id=review_id,
        item_name=item_name,
        requested_amount=requested_amount,
        approved_amount=approved_amount,
        status=status,
        rejection_reason=rejection_reason,
    )

    db.add(review_item)
    await db.commit()
    await db.refresh(review_item)

    # Update claim approved amount if MD review
    # if review.review_type == ReviewType.MD:
    claim_result = await db.execute(select(Claim).where(Claim.id == review.claim_id))
    claim = claim_result.scalar_one_or_none()

    if claim:
            item_result = await db.execute(select(ReviewItem).where(ReviewItem.review_id == review_id))
            items = item_result.scalars().all()
            total_approved = sum(item.approved_amount for item in items)

            claim.approved_amount = total_approved
            await db.commit()

    return {
        "id": review_item.id,
        "item_name": review_item.item_name,
        "requested_amount": review_item.requested_amount,
        "approved_amount": review_item.approved_amount,
        "status": review_item.status,
        "message": "Review item added successfully"
    }

@router.put("/{review_id}/items/{item_id}", response_model=dict)
async def update_review_item(
    review_id: UUID,
    item_id: UUID,
    item_name: Optional[str] = Form(None),
    requested_amount: Optional[float] = Form(None),
    approved_amount: Optional[float] = Form(None),
    status: Optional[str] = Form(None),
    rejection_reason: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
     _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Update review item
    """
    # Fetch review
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Fetch review item
    result = await db.execute(
        select(ReviewItem).where(
            ReviewItem.id == item_id,
            ReviewItem.review_id == review_id
        )
    )
    review_item = result.scalar_one_or_none()
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found")

    # # Check permissions
    # if current_user.id != review.reviewer_id and current_user.role != UserRole.ADMIN:
    #     raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Validate status
    if status and status not in [ReviewItemStatus.APPROVED, ReviewItemStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Apply updates
    if item_name is not None:
        review_item.item_name = item_name
    if requested_amount is not None:
        review_item.requested_amount = requested_amount
    if approved_amount is not None:
        review_item.approved_amount = approved_amount
    if status is not None:
        review_item.status = status
    if rejection_reason is not None:
        review_item.rejection_reason = rejection_reason

    await db.commit()
    await db.refresh(review_item)

    result = await db.execute(select(Claim).where(Claim.id == review.claim_id))
    claim = result.scalar_one_or_none()

    if claim:
            result = await db.execute(
                select(ReviewItem.approved_amount)
                .where(ReviewItem.review_id == review_id)
            )
            approved_items = result.scalars().all()
            total_approved = sum(amount for amount in approved_items if amount)
            claim.approved_amount = total_approved
            await db.commit()

    return {
        "id": review_item.id,
        "item_name": review_item.item_name,
        "requested_amount": review_item.requested_amount,
        "approved_amount": review_item.approved_amount,
        "status": review_item.status,
    } 

@router.patch("/{review_id}")
async def patch_review(  
    review_id: UUID,
    review_in: ReviewPatch,
    db: AsyncSession = Depends(get_db), 
    _: dict = Depends(access_token_bearer)
) -> Any:
   
    statement = select(Review).where(Review.id== review_id)
    result = await db.exec(statement) 
    review = result.first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    review = await base.patch(db,db_obj=Review,obj_in=review_in,id=review_id)
    return review 

@router.patch("/{review_id}/items/{item_id}")
async def patch_reviewItem(  
    item_id: UUID,
    item_in: ReviewPatch,
    db: AsyncSession = Depends(get_db), 
    _: dict = Depends(access_token_bearer)
) -> Any:
   
    statement = select(ReviewItem).where(ReviewItem.id== item_id)
    result = await db.exec(statement) 
    item = result.first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    Item = await base.patch(db,db_obj=ReviewItem,obj_in=item_in,id=item_id)
    return Item
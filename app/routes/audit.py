from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status 
from sqlmodel.ext.asyncio.session import AsyncSession 
from sqlalchemy.orm import Session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import desc 
from app.db.session import get_db 

from app.models.models import User, AuditLog, AuditAction 
from sqlmodel import select

from app.core import deps
from app.models.models import User


router = APIRouter()

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Any
from uuid import UUID 
from app.core.deps import AccessTokenBearer
from datetime import datetime  

access_token_bearer = AccessTokenBearer(auto_error=True)

@router.get("", response_model=List[dict])
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[UUID] = None,
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    _: dict = Depends(access_token_bearer)
) -> Any:
  

    # Build the base query
    query = select(AuditLog)
    
    # Apply filters if provided
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action_type:
        query = query.filter(AuditLog.action == action_type)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    # Order by timestamp descending
    query = query.order_by(desc(AuditLog.created_at))

    # ✅ Correct: execute count separately
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total_count = total_result.scalar()

    # ✅ Correct: paginate and execute the main query
    result = await db.execute(query.offset(skip).limit(limit))
    audit_logs = result.scalars().all()

    # Convert to dicts
    final_result = []
    for log in audit_logs:
        # Fetch user separately
        user_result = await db.execute(select(User).filter(User.id == log.user_id))
        user = user_result.scalar_one_or_none()

        user_name = user.full_name if user else "Unknown"
        user_email = user.email if user else "Unknown"

        log_dict = {
            "id": str(log.id),
            "timestamp": log.created_at,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_name": user_name,
            "user_email": user_email,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "details": log.details,
        }
        final_result.append(log_dict)
    
    return final_result


@router.get("/summary", response_model=dict)
async def get_audit_summary(
    db: AsyncSession = Depends(get_db),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Get summary statistics of audit logs (admin only)
    """

    base_query = select(AuditLog)

    # Apply date filters
    if start_date:
        base_query = base_query.filter(AuditLog.created_at >= start_date)
    if end_date:
        base_query = base_query.filter(AuditLog.created_at <= end_date)

    # Total count
    total_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(total_query)
    total_count = total_result.scalar()

    # Count by action
    action_counts = {}
    action_names = [a for a in dir(AuditAction) if not a.startswith("__") and not callable(getattr(AuditAction, a))]
    for action in action_names:
        action_query = base_query.filter(AuditLog.action == action)
        count_query = select(func.count()).select_from(action_query.subquery())
        count_result = await db.execute(count_query)
        action_counts[action] = count_result.scalar()

    # Count by entity type
    entity_counts = {}
    entity_type_result = await db.execute(
        select(AuditLog.entity_type).distinct().filter(AuditLog.entity_type.isnot(None))
    )
    distinct_entity_types = entity_type_result.scalars().all()

    for entity_type in distinct_entity_types:
        count_query = select(func.count()).select_from(
            base_query.filter(AuditLog.entity_type == entity_type).subquery()
        )
        count_result = await db.execute(count_query)
        entity_counts[entity_type] = count_result.scalar()

    # Count by user
    user_counts = {}
    user_id_result = await db.execute(
        select(AuditLog.user_id).distinct().filter(AuditLog.user_id.isnot(None))
    )
    user_ids = user_id_result.scalars().all()

    for user_id in user_ids:
        count_query = select(func.count()).select_from(
            base_query.filter(AuditLog.user_id == user_id).subquery()
        )
        count_result = await db.execute(count_query)

        user_result = await db.execute(select(User).filter(User.id == user_id))
        user_obj = user_result.scalar_one_or_none()
        user_name = user_obj.full_name if user_obj else "Unknown"

        user_counts[str(user_id)] = {
            "count": count_result.scalar(),
            "user_name": user_name
        }

    return {
        "total_count": total_count,
        "action_counts": action_counts,
        "entity_counts": entity_counts,
        "user_counts": user_counts,
    }


@router.get("/{log_id}", response_model=dict)
async def get_audit_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(access_token_bearer)
) -> Any:
    """
    Get a specific audit log by ID (admin only)
    """
    result = await db.execute(select(AuditLog).filter(AuditLog.id == log_id))
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    
    # Fetch user details
    user_result = await db.execute(select(User).filter(User.id == log.user_id))
    user = user_result.scalar_one_or_none()
    user_name = user.full_name if user else "Unknown"
    user_email = user.email if user else "Unknown"

    return {
        "id": str(log.id),
        "timestamp": log.created_at,
        "user_id": str(log.user_id),
        "user_name": user_name,
        "user_email": user_email,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": str(log.entity_id) if log.entity_id else None,
        "details": log.details,
    }

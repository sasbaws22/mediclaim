from fastapi import APIRouter, Depends,status,Request
from fastapi.exceptions import HTTPException 
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.session import get_db 
from app.core.deps import AccessTokenBearer
from app.core.deps import get_current_user
from typing import List,Optional 
from app.cruds.base import CRUDBase
from app.models.models import Policy,User
from app.schemas.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyPatch,
    PolicyResponse 
)
base = CRUDBase(Policy)
router = APIRouter()
access_token_bearer = AccessTokenBearer()



@router.post("") 
async def create_policy(
    resource_data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
   
    _: dict = Depends(access_token_bearer)
    ): 
    # Generate unique member number
    member_number = f"MEM-{uuid.uuid4().hex[:7].upper()}"
    policy_to_dict = resource_data.model_dump()
    new_policy = Policy(** policy_to_dict) 

    new_policy.member_number = member_number 

    db.add(new_policy)
        
    await db.commit()

    await db.refresh(new_policy)

    return new_policy




@router.get("")
async def get_policy(
    plan_type :Optional[str]=None,
    start_date:Optional[str]=None,
    end_date:Optional[str]=None,
    is_active:Optional[bool]=None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(access_token_bearer)
    ):
      query = select(Policy)
      if plan_type:
        query = query.where(Policy.plan_type == plan_type) 
      
      if start_date:
        query = query.where(Policy.start_date == start_date)

      if end_date:
        query = query.where(Policy.end_date == end_date) 
     
      if is_active:
        query = query.where(Policy.is_active == is_active) 

      result = await db.exec(query)

      return result

@router.get("/{resource_id}")
async def get_policy(
    resource_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
   _: dict = Depends(access_token_bearer)
    ):
     statement = select(Policy).where(Policy.id== resource_id)
     result = await db.exec(statement)
     policy = result.first()

     return policy if policy is not None else None 



@router.put("/{resource_id}") 
async def update_policy(
    resource_id: uuid.UUID,
      policy_data: PolicyUpdate , 
      db: AsyncSession = Depends(get_db),
      _: dict = Depends(access_token_bearer)
      ): 
      statement = select(Policy).where(Policy.id== resource_id)
      result = await db.exec(statement)
      policy_to_update = result.first()
      if policy_to_update is not None:
            policy_to_update_dict = policy_data.model_dump()
            for k, v in policy_to_update_dict.items():
                setattr(policy_to_update, k, v)
            await db.commit()
            await db.refresh(policy_to_update)

            return policy_to_update
      else:
            return None 

@router.patch("/{resource_id}")
async def patch_policy(  
    resource_id: uuid.UUID,
    policy_in:PolicyPatch,
    db: AsyncSession = Depends(get_db), 
    _: dict = Depends(access_token_bearer)
  ):
   
    statement = select(Policy).where(Policy.id== resource_id)
    result = await db.exec(statement)
    policy = result.first()
    if policy is not None:
      raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    policy = await base.patch(db,db_obj=policy,obj_in=policy_in,id=resource_id)
    return policy


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    resource_id: str,
    db: AsyncSession = Depends(get_db), 
   _: dict = Depends(access_token_bearer)
    ):
      statement = select(Policy).where(Policy.id== resource_id)
      result = await db.exec(statement)
      policy_to_delete = result.first()
      if policy_to_delete is not None:
        await db.delete(policy_to_delete)
        await db.commit()
        return {}
      else:
       
       return None 

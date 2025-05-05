from fastapi import APIRouter, Depends,status,Request
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.session import get_db
from app.core.deps import get_current_admin_user
from typing import List,Optional 
from app.models.models import Employer,User
from app.schemas.employer import (
    EmployerCreate,
    EmployerUpdate
   
)

router = APIRouter()




@router.post("") 
async def create_employer(
    resource_data: EmployerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
    ):
    employer_to_dict = resource_data.model_dump()
    new_employer = Employer(** employer_to_dict)
    db.add(new_employer)
        
    await db.commit()

    await db.refresh(new_employer)

    return new_employer




@router.get("")
async def get_employer(
    name :Optional[str]=None,
    contact_person:Optional[str]=None,
    contact_email:Optional[str]=None,
    contact_phone:Optional[str]=None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
    ):
      query = select(Employer)
      if name:
        query = query.where(Employer.name == name) 
      
      if contact_person:
        query = query.where(Employer.contact_person == contact_person)

      if contact_email:
        query = query.where(Employer.contact_email == contact_email) 
     
      if contact_phone:
        query = query.where(Employer.contact_phone == contact_phone) 

      result = await db.exec(query)

      return result

@router.get("/{resource_id}")
async def get_employer(
    resource_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_admin_user)
    ):
     statement = select(Employer).where(Employer.id== resource_id)
     result = await db.exec(statement)
     employer = result.first()

     return employer if employer is not None else None 



@router.put("/{resource_id}") 
async def update_employer(
    resource_id: str, 
    employer_data: EmployerUpdate , 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user) 
    ): 
      statement = select(Employer).where(Employer.id== resource_id)
      result = await db.exec(statement)
      employer_to_update = result.first()
      if employer_to_update is not None:
            employer_to_update_dict = employer_data.model_dump()
            for k, v in employer_to_update_dict.items():
                setattr(employer_to_update, k, v)
            await db.commit()
            await db.refresh(employer_to_update)

            return employer_to_update
      else:
            return None 

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employer(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)):
      statement = select(Employer).where(Employer.id== resource_id)
      result = await db.exec(statement)
      employer_to_delete = result.first()
      if employer_to_delete is not None:
        await db.delete(employer_to_delete)
        await db.commit()
        return {}
      else:
       
       return None 

from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field   




class ClaimCreate(BaseModel):

    reference_number:str
    policy_id:Optional[UUID]
    hospital_pharmacy:str
    reason:str
    requested_amount:float
    approved_amount:float 
    status:str
    submission_date:datetime 
  

class ClaimResponse(BaseModel):

    id: Optional[ UUID ]
    reference_number:str
    policy_id:Optional[UUID]
    hospital_pharmacy:str
    reason:str
    requested_amount:float
    approved_amount:float 
    status:str
    submission_date:datetime 
    created_at:datetime 
    updated_at:datetime 

class ClaimPatch(BaseModel):

    reference_number:Optional[str] = None
    policy_id:Optional[UUID] = None
    hospital_pharmacy: Optional[str] = None
    reason: Optional[str] = None
    requested_amount: Optional[float] = None
    approved_amount:Optional[float ] = None
    status:Optional[str] = None
    submission_date:Optional[datetime ] = None 

class AttachmentPatch(BaseModel):
    
    claim_id :Optional[UUID] = None 
    file_name: Optional[str ]
    

    class Config:
        from_attributes = True

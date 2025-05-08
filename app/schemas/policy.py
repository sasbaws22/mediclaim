from pydantic import BaseModel
from datetime import datetime,date
from typing import List, Optional,List
import uuid
   

class PolicyCreate(BaseModel):
    plan_type  :str  
    policyholder_id:uuid.UUID
    employer_id:uuid.UUID
    start_date: datetime 
    end_date: datetime
    is_active: bool 
   

   

class PolicyUpdate(BaseModel):
    plan_type  :str  
    policyholder_id:uuid.UUID
    employer_id:uuid.UUID
    start_date: datetime 
    end_date: datetime
    is_active: bool  


class PolicyPatch(BaseModel):
    plan_type  : Optional[str ] = None
    policyholder_id:Optional[uuid.UUID] = None
    employer_id:Optional[uuid.UUID] = None
    start_date: Optional[datetime]  = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

     

class PolicyResponse(BaseModel): 
     uid : uuid.UUID
     plan_type  :str  
     start_date: datetime 
     end_date: datetime
     is_active: bool 
     created_at:datetime 
     updated_at:datetime 



    
     class Config:
        from_attributes = True




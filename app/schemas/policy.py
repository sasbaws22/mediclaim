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

     

class PolicyResponse(BaseModel): 
     uid : uuid.UUID
     plan_type  :str  
     start_date: datetime 
     end_date: datetime
     is_active: bool 
     created_at:datetime 
     updated_at:datetime 



    
     class Config:
        orm_mode = True




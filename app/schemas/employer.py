from pydantic import BaseModel
from datetime import datetime,date
from typing import List, Optional,List
import uuid
   

class EmployerCreate(BaseModel):
    name :str 
    contact_person :str
    contact_email  :str 
    contact_phone  :str 
   

class EmployerUpdate(BaseModel):
     name :Optional[str] =None
     contact_person :Optional[str] = None
     contact_email  :Optional[str] = None 
     contact_phone  :Optional[str] = None
     

class EmployerResponse(BaseModel): 
     uid : uuid.UUID
     name :str 
     contact_person :str
     contact_email  :str 
     contact_phone  :str
     created_at :datetime 
     updated_at :datetime



    
     class Config:
        orm_mode = True



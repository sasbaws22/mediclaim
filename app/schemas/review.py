from pydantic import BaseModel
from datetime import datetime,date
from typing import List, Optional,List
import uuid


class ReviewCreate(BaseModel):
    
    claim_id:Optional[uuid.UUID]
    reviewer_id:Optional[uuid.UUID]
    review_type:str
    comments:str 
    decision:str 
    rejection_reason:str 

   

class ReviewResponse(BaseModel):
    id  : uuid.UUID 
    claim_id:Optional[uuid.UUID]
    reviewer_id:Optional[uuid.UUID]
    review_type:str
    comments:str 
    decision:str 
    rejection_reason:str 
    reviewed_at:datetime 
    created_at:datetime 
    updated_at:datetime  

class ReviewPatch(BaseModel):

    claim_id:Optional[uuid.UUID] = None
    reviewer_id:Optional[uuid.UUID] = None
    review_type:Optional[str] = None
    comments:Optional[str ] = None
    decision:Optional[str] = None
    rejection_reason:Optional[str ] = None
    
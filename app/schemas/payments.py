from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

from pydantic import BaseModel, Field



class PaymentCreate(BaseModel):
    claim_id  :Optional[UUID] 
    invoice_number:str 
    payment_amount:float
    payment_date:date  
    payment_status:str 
    processed_by_id :Optional[UUID]
   

class PaymentResponse(BaseModel):
    id: UUID
    claim_id  :Optional[UUID] 
    invoice_number:str 
    payment_amount:float
    payment_date:date  
    payment_status:str 
    processed_by_id :Optional[UUID] 
    created_at:datetime
    updated_at:datetime


class PaymentPatch(BaseModel):
    claim_id :Optional[UUID] = None
    invoice_number: Optional[str] = None 
    payment_amount: Optional[float] = None 
    payment_date: Optional[date] = None 
    payment_status:Optional[str] = None 
    processed_by_id :Optional[UUID] = None
    

    class Config:
        from_attributes = True

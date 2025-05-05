from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, Dict, Any

class AuditLogBase(BaseModel):
    user_id: UUID4
    action: str
    entity_type: str
    entity_id: Optional[UUID4] = None
    details: Optional[Dict[str, Any]] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: UUID4
    timestamp: datetime

    class Config:
        from_attributes = True

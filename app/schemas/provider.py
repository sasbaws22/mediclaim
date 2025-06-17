from typing import Optional
from uuid import UUID
from sqlmodel import Field, SQLModel

class ProviderBase(SQLModel):
    name: str
    contact_person: str
    contact_email: str
    contact_phone: str

class ProviderCreate(ProviderBase):
    pass

class ProviderRead(ProviderBase):
    id: UUID

class ProviderUpdate(SQLModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None



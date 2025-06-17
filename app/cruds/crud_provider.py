from app.cruds.base import CRUDBase
from app.models.models import Provider
from app.schemas.provider import ProviderCreate, ProviderRead, ProviderUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import Optional

class CRUDProvider(CRUDBase[Provider, ProviderCreate, ProviderRead, ProviderUpdate]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Provider]:
        statement = select(self.model).filter(self.model.contact_email == email)
        result = await db.exec(statement)
        return result.first()

provider = CRUDProvider(Provider)


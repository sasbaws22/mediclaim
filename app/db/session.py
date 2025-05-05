from sqlmodel import SQLModel,create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker 
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

async_engine = AsyncEngine(create_engine(url=settings.DATABASE_URL))

async def get_db():
    Session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with Session() as db:
        yield db
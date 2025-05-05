from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel,select


ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
PatchSchemaType = TypeVar("PatchSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType,PatchSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLModel model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    async def get(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        statement = select(self.model).filter(self.model.id== id)
        result = await db.exec(statement)
        obj = result.first()
        return obj 
    
    async  def get_multi(
        self, db: AsyncSession,skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
             statement= select(self.model).offset(skip).limit(limit)
             result = await db.execute(statement)
             obj =result.scalar()
             return obj

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj 
    

    async def patch(
       self,
       db: AsyncSession,
      db_obj: ModelType,
      id: UUID,
      obj_in: Union[PatchSchemaType, Dict[str, Any]]
    ) -> ModelType:
    # Build and execute the query
      statement = select(self.model).where(self.model.id == id)
      result = await db.execute(statement)
      existing_obj = result.scalars().first()

     # Handle not found
      if not existing_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{self.model.__name__} with id {id} not found"
        )

     # Extract the data to update
      patch_data = obj_in.model_dump(exclude_unset=True)

     # Apply patch
      for field, value in patch_data.items():
        setattr(existing_obj, field, value)

      db.add(existing_obj)
      await db.commit()
      await db.refresh(existing_obj)

      return existing_obj

    async def remove(self, db: AsyncSession, *, id: UUID) -> ModelType:
        obj = select(self.model).where(self.model[id]==id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with id {id} not found",
            )
        db.delete(obj)
        db.commit()
        return obj

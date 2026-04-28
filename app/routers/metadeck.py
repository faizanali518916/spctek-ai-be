import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.database import get_db
from app.models.metadeck import Metadeck
from app.schemas.metadeck import MetadeckRead, MetadeckCreate, MetadeckUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadeck", tags=["Metadeck"])


@router.post("", response_model=MetadeckRead, status_code=status.HTTP_201_CREATED)
async def create_metadeck(metadeck_data: MetadeckCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new metadeck entry.
    """
    db_metadeck = Metadeck(**metadeck_data.model_dump())

    db.add(db_metadeck)
    await db.commit()
    await db.refresh(db_metadeck)
    return db_metadeck


@router.get("", response_model=List[MetadeckRead])
async def list_metadeck(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a list of metadeck entries.
    """
    result = await db.execute(select(Metadeck).order_by(Metadeck.path.asc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/page/{path}", response_model=MetadeckRead)
async def get_metadeck_by_path(path: str, db: AsyncSession = Depends(get_db)):
    """
    Get metadeck entry by page path (e.g., /about).
    """
    result = await db.execute(select(Metadeck).where(Metadeck.path == path))
    metadeck = result.scalar_one_or_none()

    if not metadeck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadeck entry not found")
    return metadeck


@router.get("/{metadeck_id}", response_model=MetadeckRead)
async def get_metadeck(metadeck_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a specific metadeck entry by UUID.
    """
    result = await db.execute(select(Metadeck).where(Metadeck.id == metadeck_id))
    metadeck = result.scalar_one_or_none()

    if not metadeck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadeck entry not found")
    return metadeck


@router.patch("/{metadeck_id}", response_model=MetadeckRead)
async def update_metadeck(metadeck_id: uuid.UUID, metadeck_data: MetadeckUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update metadeck entry. Supports partial updates via PATCH.
    """
    result = await db.execute(select(Metadeck).where(Metadeck.id == metadeck_id))
    db_metadeck = result.scalar_one_or_none()

    if not db_metadeck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadeck entry not found")

    # Convert schema to dict, excluding fields not explicitly set
    update_dict = metadeck_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(db_metadeck, key, value)

    await db.commit()
    await db.refresh(db_metadeck)
    return db_metadeck


@router.delete("/{metadeck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metadeck(metadeck_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a metadeck entry.
    """
    result = await db.execute(select(Metadeck).where(Metadeck.id == metadeck_id))
    db_metadeck = result.scalar_one_or_none()

    if not db_metadeck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadeck entry not found")

    await db.delete(db_metadeck)
    await db.commit()
    return None

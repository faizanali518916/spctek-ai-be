import uuid
from typing import Optional
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.popup import Popup
from app.schemas.popup import PopupCreate, PopupRead, PopupUpdate

router = APIRouter(prefix="/popups", tags=["Popups"])


@router.post("", response_model=PopupRead, status_code=status.HTTP_201_CREATED)
async def create_popup(popup_data: PopupCreate, db: AsyncSession = Depends(get_db)):
    db_popup = Popup(**popup_data.model_dump())
    db.add(db_popup)
    await db.commit()
    await db.refresh(db_popup)
    return db_popup


@router.get("", response_model=List[PopupRead])
async def list_popups(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Popup).order_by(Popup.path.asc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/by-path", response_model=Optional[PopupRead])
async def get_popup_by_path(path: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Popup).where(Popup.path == path))
    popup = result.scalar_one_or_none()

    if not popup:
        return None

    return popup


@router.get("/{popup_id}", response_model=PopupRead)
async def get_popup(popup_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Popup).where(Popup.id == popup_id))
    popup = result.scalar_one_or_none()

    if not popup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Popup not found")

    return popup


@router.patch("/{popup_id}", response_model=PopupRead)
async def update_popup(popup_id: uuid.UUID, popup_data: PopupUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Popup).where(Popup.id == popup_id))
    db_popup = result.scalar_one_or_none()

    if not db_popup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Popup not found")

    update_dict = popup_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_popup, key, value)

    await db.commit()
    await db.refresh(db_popup)
    return db_popup


@router.delete("/{popup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_popup(popup_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Popup).where(Popup.id == popup_id))
    db_popup = result.scalar_one_or_none()

    if not db_popup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Popup not found")

    await db.delete(db_popup)
    await db.commit()
    return None

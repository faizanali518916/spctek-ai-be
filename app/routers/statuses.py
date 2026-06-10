import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.contact import Contact
from app.models.status import Status
from app.schemas.status import StatusCreate, StatusRead, StatusUpdate

router = APIRouter(prefix="/statuses", tags=["Statuses"])


async def _status_response(status_id: uuid.UUID, db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(Status.id, Status.code, func.count(Contact.id).label("contact_count"))
        .outerjoin(Contact, Contact.status_id == Status.id)
        .where(Status.id == status_id)
        .group_by(Status.id, Status.code)
    )
    row = result.one_or_none()
    if row is None:
        return None

    return {
        "id": row.id,
        "code": row.code,
        "contact_count": row.contact_count,
    }


@router.post("", response_model=StatusRead, status_code=status.HTTP_201_CREATED)
async def create_status(status_data: StatusCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Status).where(Status.code == status_data.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A status with this code already exists",
        )

    status_row = Status(code=status_data.code)
    db.add(status_row)
    await db.commit()
    await db.refresh(status_row)
    return {
        "id": status_row.id,
        "code": status_row.code,
        "contact_count": 0,
    }


@router.get("", response_model=list[StatusRead])
async def list_statuses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Status.id, Status.code, func.count(Contact.id).label("contact_count"))
        .outerjoin(Contact, Contact.status_id == Status.id)
        .group_by(Status.id, Status.code)
        .order_by(Status.code.asc())
    )
    return [
        {
            "id": row.id,
            "code": row.code,
            "contact_count": row.contact_count,
        }
        for row in result
    ]


@router.get("/{status_id}", response_model=StatusRead)
async def get_status(status_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    status_row = await _status_response(status_id, db)
    if status_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status not found",
        )
    return status_row


@router.put("/{status_id}", response_model=StatusRead)
async def update_status(status_id: uuid.UUID, status_data: StatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Status).where(Status.id == status_id))
    status_row = result.scalar_one_or_none()
    if status_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status not found",
        )

    duplicate = await db.execute(select(Status).where(Status.id != status_id, Status.code == status_data.code))
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A status with this code already exists",
        )

    status_row.code = status_data.code
    await db.commit()
    updated_status = await _status_response(status_id, db)
    if updated_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status not found",
        )
    return updated_status


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_status(status_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Status).where(Status.id == status_id))
    status_row = result.scalar_one_or_none()
    if status_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status not found",
        )

    await db.delete(status_row)
    await db.commit()

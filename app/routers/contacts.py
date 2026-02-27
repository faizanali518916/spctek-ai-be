from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactRead

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.post("/", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_data: ContactCreate, db: AsyncSession = Depends(get_db)
):
    if not contact_data.email and not contact_data.phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least an email or phone number is required",
        )

    contact = Contact(**contact_data.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/", response_model=list[ContactRead])
async def list_contacts(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()

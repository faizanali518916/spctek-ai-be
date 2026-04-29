import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services.email import send_form_submission_email, send_contact_thank_you_email

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_data: ContactCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
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

    # Send email in background if email is provided
    if contact_data.email:
        if contact_data.source in ["process_diagnostic", "ai_deployment_roadmap", "ai_playbook"]:
            # Send form report email
            background_tasks.add_task(
                send_form_submission_email,
                recipient_email=contact_data.email,
                recipient_name=contact_data.name or "there",
                source=contact_data.source,
                journey_data=contact_data.journey or {},
            )
        elif contact_data.source == "website":
            # Send thank you email for contact form
            background_tasks.add_task(
                send_contact_thank_you_email,
                recipient_email=contact_data.email,
                recipient_name=contact_data.name or "there",
                company=contact_data.company or "",
                message=contact_data.message or "",
            )

    return contact


@router.get("", response_model=list[ContactRead])
async def list_contacts(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(contact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    return contact


@router.put("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: uuid.UUID,
    contact_data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    update_data = contact_data.model_dump(exclude_unset=True)
    if "email" in update_data and not update_data.get("email") and not contact.phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least an email or phone number is required",
        )
    if "phone" in update_data and not update_data.get("phone") and not contact.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least an email or phone number is required",
        )

    for field, value in update_data.items():
        if field == "journey" and contact.journey:
            merged_journey = {**contact.journey, **value}
            setattr(contact, field, merged_journey)
        else:
            setattr(contact, field, value)

    if not contact.email and not contact.phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least an email or phone number is required",
        )

    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    await db.delete(contact)
    await db.commit()

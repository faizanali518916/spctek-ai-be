import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.contact import Contact, ContactSubmission
from app.schemas.contact import ContactCreate, ContactRead, ContactSubmissionRead, ContactUpdate
from app.services.email import send_form_submission_email, send_contact_thank_you_email

router = APIRouter(prefix="/contacts", tags=["Contacts"])


def _latest_submission(contact: Contact) -> ContactSubmission | None:
    if not contact.submissions:
        return None

    return max(
        contact.submissions,
        key=lambda submission: submission.created_at or datetime.min.replace(tzinfo=timezone.utc),
    )


def _submission_response(submission: ContactSubmission, email: str | None = None) -> dict:
    return {
        "id": submission.id,
        "name": submission.name,
        "email": email or (submission.contact.email if submission.contact else None),
        "phone": submission.phone,
        "company": submission.company,
        "message": submission.message,
        "source": submission.source,
        "journey": submission.journey,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


def _contact_response(contact: Contact, detail: bool = False) -> dict:
    latest_submission = _latest_submission(contact)
    response = {
        "id": contact.id,
        "email": contact.email,
        "name": latest_submission.name if latest_submission else None,
        "phone": latest_submission.phone if latest_submission else None,
        "company": latest_submission.company if latest_submission else None,
        "message": latest_submission.message if latest_submission else None,
        "source": latest_submission.source if latest_submission else None,
        "journey": latest_submission.journey if latest_submission else None,
        "created_at": latest_submission.created_at if latest_submission else None,
        "updated_at": latest_submission.updated_at if latest_submission else None,
    }

    if detail:
        submissions = sorted(
            contact.submissions,
            key=lambda submission: submission.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        response["submissions"] = [_submission_response(submission, contact.email) for submission in submissions]

    return response


def _submission_payload(
    contact_data: ContactCreate | ContactUpdate,
    contact: Contact | None = None,
    provided_fields: set[str] | None = None,
) -> dict:
    latest_submission = _latest_submission(contact) if contact else None

    def field_value(field_name: str, fallback):
        if provided_fields is None or field_name in provided_fields:
            return getattr(contact_data, field_name)
        return fallback

    return {
        "name": field_value("name", latest_submission.name if latest_submission else None),
        "phone": field_value("phone", latest_submission.phone if latest_submission else None),
        "company": field_value("company", latest_submission.company if latest_submission else None),
        "message": field_value("message", latest_submission.message if latest_submission else None),
        "source": field_value("source", latest_submission.source if latest_submission else "landing_page"),
        "journey": field_value("journey", latest_submission.journey if latest_submission else {}),
    }


async def _load_contacts(db: AsyncSession) -> list[Contact]:
    result = await db.execute(select(Contact).options(selectinload(Contact.submissions)))
    return result.scalars().unique().all()


@router.post("", response_model=ContactRead, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_data: ContactCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if not contact_data.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required",
        )

    result = await db.execute(
        select(Contact).options(selectinload(Contact.submissions)).where(Contact.email == contact_data.email)
    )
    contact = result.scalar_one_or_none()

    if contact is None:
        contact = Contact(email=contact_data.email)
        db.add(contact)
        await db.flush()
        submission_payload = _submission_payload(contact_data)
    else:
        submission_payload = _submission_payload(contact_data, contact)

    submission = ContactSubmission(contact_id=contact.id, **submission_payload)
    db.add(submission)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

        result = await db.execute(
            select(Contact).options(selectinload(Contact.submissions)).where(Contact.email == contact_data.email)
        )
        contact = result.scalar_one_or_none()
        if contact is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create contact")

        submission = ContactSubmission(contact_id=contact.id, **_submission_payload(contact_data, contact))
        db.add(submission)
        await db.commit()

    await db.refresh(submission)

    if contact_data.email:
        if contact_data.source in ["process_diagnostic", "ai_deployment_roadmap", "ai_playbook"]:
            background_tasks.add_task(
                send_form_submission_email,
                recipient_email=contact_data.email,
                recipient_name=contact_data.name or "there",
                source=contact_data.source,
                journey_data=contact_data.journey or {},
            )
        elif contact_data.source == "website":
            background_tasks.add_task(
                send_contact_thank_you_email,
                recipient_email=contact_data.email,
                recipient_name=contact_data.name or "there",
                company=contact_data.company or "",
                message=contact_data.message or "",
            )

    return {
        "id": contact.id,
        "email": contact.email,
        "name": submission.name,
        "phone": submission.phone,
        "company": submission.company,
        "message": submission.message,
        "source": submission.source,
        "journey": submission.journey,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


@router.get("", response_model=list[ContactRead], response_model_exclude_none=True)
async def list_contacts(
    skip: int = 0,
    limit: int = 50,
    detail: bool = Query(False, description="Include all contact submissions in the response"),
    db: AsyncSession = Depends(get_db),
):
    contacts = await _load_contacts(db)

    def contact_sort_key(contact: Contact) -> datetime:
        latest_submission = _latest_submission(contact)
        return (
            latest_submission.created_at
            if latest_submission and latest_submission.created_at
            else datetime.min.replace(tzinfo=timezone.utc)
        )

    contacts.sort(key=contact_sort_key, reverse=True)
    return [_contact_response(contact, detail=detail) for contact in contacts[skip : skip + limit]]


@router.get("/{contact_id}", response_model=ContactRead, response_model_exclude_none=True)
async def get_contact(
    contact_id: uuid.UUID,
    detail: bool = Query(False, description="Include all contact submissions in the response"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).options(selectinload(Contact.submissions)).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    return _contact_response(contact, detail=detail)


@router.put("/{contact_id}", response_model=ContactRead, response_model_exclude_none=True)
async def update_contact(
    contact_id: uuid.UUID,
    contact_data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).options(selectinload(Contact.submissions)).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    update_data = contact_data.model_dump(exclude_unset=True)
    if "email" in update_data and not update_data.get("email"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required",
        )

    if "email" in update_data:
        existing_contact_result = await db.execute(
            select(Contact).where(Contact.email == update_data["email"], Contact.id != contact.id)
        )
        if existing_contact_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A contact with this email already exists",
            )
        contact.email = update_data["email"]

    should_append_submission = any(
        field in update_data for field in ("name", "phone", "company", "message", "source", "journey")
    )
    if should_append_submission:
        submission = ContactSubmission(
            contact_id=contact.id,
            **_submission_payload(contact_data, contact, provided_fields=set(update_data)),
        )
        db.add(submission)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A contact with this email already exists",
        )
    await db.refresh(contact)

    if should_append_submission:
        await db.refresh(submission)
        return {
            "id": contact.id,
            "email": contact.email,
            "name": submission.name,
            "phone": submission.phone,
            "company": submission.company,
            "message": submission.message,
            "source": submission.source,
            "journey": submission.journey,
            "created_at": submission.created_at,
            "updated_at": submission.updated_at,
        }

    return _contact_response(contact)


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

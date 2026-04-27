import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.database import get_db
from app.models.author import Author
from app.schemas.author import AuthorRead, AuthorCreate, AuthorUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/authors", tags=["Authors"])


@router.post("", response_model=AuthorRead, status_code=status.HTTP_201_CREATED)
async def create_author(author_data: AuthorCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new author. social_links should be a dict: {"linkedin": "url", ...}
    """
    # Check if author with same name exists (Optional, depending on your business logic)
    db_author = Author(**author_data.model_dump())

    db.add(db_author)
    await db.commit()
    await db.refresh(db_author)
    return db_author


@router.get("", response_model=List[AuthorRead])
async def list_authors(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a list of authors.
    """
    result = await db.execute(select(Author).order_by(Author.name.asc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{author_id}", response_model=AuthorRead)
async def get_author(author_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a specific author by UUID.
    """
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()

    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    return author


@router.patch("/{author_id}", response_model=AuthorRead)
async def update_author(author_id: uuid.UUID, author_data: AuthorUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update author details. Supports partial updates via PATCH.
    """
    result = await db.execute(select(Author).where(Author.id == author_id))
    db_author = result.scalar_one_or_none()

    if not db_author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    # Convert schema to dict, excluding fields not explicitly set
    update_dict = author_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(db_author, key, value)

    await db.commit()
    await db.refresh(db_author)
    return db_author


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_author(author_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete an author.
    Note: If Content has a ForeignKey to Author, this may fail or nullify
    depending on your 'ondelete' configuration.
    """
    result = await db.execute(select(Author).where(Author.id == author_id))
    db_author = result.scalar_one_or_none()

    if not db_author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    await db.delete(db_author)
    await db.commit()
    return None

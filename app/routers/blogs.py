import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.blog import Blog
from app.schemas.blog import BlogCreate, BlogRead, BlogUpdate

router = APIRouter(prefix="/blogs", tags=["Blogs"])


@router.post("/", response_model=BlogRead, status_code=status.HTTP_201_CREATED)
async def create_blog(blog_data: BlogCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Blog).where(Blog.slug == blog_data.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A blog with this slug already exists",
        )

    blog = Blog(**blog_data.model_dump())
    db.add(blog)
    await db.commit()
    await db.refresh(blog)
    return blog


@router.get("/", response_model=list[BlogRead])
async def list_blogs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Blog).order_by(Blog.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{blog_id}", response_model=BlogRead)
async def get_blog(blog_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Blog).where(Blog.id == blog_id))
    blog = result.scalar_one_or_none()
    if blog is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found",
        )
    return blog


@router.put("/{blog_id}", response_model=BlogRead)
async def update_blog(
    blog_id: uuid.UUID,
    blog_data: BlogUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Blog).where(Blog.id == blog_id))
    blog = result.scalar_one_or_none()
    if blog is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found",
        )

    update_data = blog_data.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != blog.slug:
        existing = await db.execute(
            select(Blog).where(Blog.slug == update_data["slug"])
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A blog with this slug already exists",
            )

    for field, value in update_data.items():
        setattr(blog, field, value)

    await db.commit()
    await db.refresh(blog)
    return blog


@router.delete("/{blog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog(blog_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Blog).where(Blog.id == blog_id))
    blog = result.scalar_one_or_none()
    if blog is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found",
        )

    await db.delete(blog)
    await db.commit()

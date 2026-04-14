import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.blog import Blog
from app.schemas.blog import BlogCreate, BlogRead, BlogUpdate
from app.config import get_settings
from app.routers.r2 import get_r2_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blogs", tags=["Blogs"])


def extract_r2_key(url: str, settings) -> str | None:
    if not url:
        return None

    # Try parsing public base URL first
    public_base = (settings.R2_PUBLIC_BASE_URL or "").rstrip("/")
    if public_base and url.startswith(public_base):
        remaining = url[len(public_base) :].lstrip("/")

        if public_base.endswith(".r2.cloudflarestorage.com"):
            bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
            if remaining.startswith(bucket_prefix):
                return remaining[len(bucket_prefix) :]

        return remaining

    # Also handle R2_S3_API_ENDPOINT in case it was used directly
    endpoint = (settings.R2_S3_API_ENDPOINT or "").rstrip("/")
    if not endpoint:
        endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    if url.startswith(endpoint):
        remaining = url[len(endpoint) :].lstrip("/")
        bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
        if remaining.startswith(bucket_prefix):
            return remaining[len(bucket_prefix) :]

    return None


def extract_all_blog_images(blog: Blog, settings) -> list[str]:
    keys = []

    # Extract thumbnail
    if blog.thumbnail_url:
        k = extract_r2_key(blog.thumbnail_url, settings)
        if k:
            keys.append(k)

    # Extract images from content
    if blog.content:
        try:
            content_data = json.loads(blog.content)
            blocks = content_data.get("blocks", [])
            for block in blocks:
                if block.get("type") == "image":
                    file_data = block.get("data", {}).get("file", {})
                    url = file_data.get("url")
                    if url:
                        k = extract_r2_key(url, settings)
                        if k:
                            keys.append(k)
        except Exception as e:
            logger.warning(f"Error parsing blog content for images: {e}")

    return list(set(keys))


@router.post("", response_model=BlogRead, status_code=status.HTTP_201_CREATED)
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


@router.get("", response_model=list[BlogRead])
async def list_blogs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Blog).order_by(Blog.created_at.desc()).offset(skip).limit(limit))
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
        existing = await db.execute(select(Blog).where(Blog.slug == update_data["slug"]))
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

    # Automatically delete associated images from R2
    from app.config import get_settings

    settings = get_settings()
    if settings.R2_BUCKET_NAME:
        image_keys = extract_all_blog_images(blog, settings)
        if image_keys:
            try:
                from app.routers.r2 import get_r2_client

                client = get_r2_client()

                # Delete objects in batches (max 1000 per request for boto3)
                delete_requests = [{"Key": k} for k in image_keys]
                for i in range(0, len(delete_requests), 1000):
                    batch = delete_requests[i : i + 1000]
                    client.delete_objects(Bucket=settings.R2_BUCKET_NAME, Delete={"Objects": batch, "Quiet": True})
            except Exception as e:
                logger.error(f"Failed to delete images from R2 for blog {blog_id}: {e}")

    await db.delete(blog)
    await db.commit()

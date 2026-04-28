import uuid
import logging
from enum import Enum
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.models.author import Author
from app.models.category import Category
from app.models.content import Content, ContentType
from app.schemas.content import ContentCreate, ContentRead, ContentUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


class LookupField(str, Enum):
    UUID = "uuid"
    SLUG = "slug"


async def get_categories_by_ids(category_ids: list[uuid.UUID], db: AsyncSession) -> list[Category]:
    if not category_ids:
        return []

    result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
    categories = result.scalars().all()

    found_ids = {category.id for category in categories}
    missing_ids = [str(category_id) for category_id in category_ids if category_id not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category_ids: {', '.join(missing_ids)}",
        )

    category_by_id = {category.id: category for category in categories}
    return [category_by_id[category_id] for category_id in category_ids]


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


def extract_all_content_images(content: Content, settings) -> list[str]:
    keys = []

    # Extract thumbnail
    if content.thumbnail_url:
        k = extract_r2_key(content.thumbnail_url, settings)
        if k:
            keys.append(k)

    # Extract images from content
    if content.content and isinstance(content.content, dict):
        try:
            blocks = content.content.get("blocks", [])
            for block in blocks:
                if block.get("type") == "image":
                    file_data = block.get("data", {}).get("file", {})
                    url = file_data.get("url")
                    if url:
                        k = extract_r2_key(url, settings)
                        if k:
                            keys.append(k)
        except Exception as e:
            logger.warning(f"Error parsing content body for images: {e}")

    return list(set(keys))


@router.post("", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
async def create_content(content_data: ContentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Content).where(Content.slug == content_data.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A content item with this slug already exists",
        )

    payload = content_data.model_dump(exclude={"category_ids"})
    content = Content(**payload)
    content.categories = await get_categories_by_ids(content_data.category_ids, db)

    db.add(content)
    await db.commit()

    created = await db.execute(
        select(Content).options(selectinload(Content.categories)).where(Content.id == content.id)
    )
    return created.scalar_one()


@router.get("", response_model=list[ContentRead])
async def list_content(
    content_type: ContentType = Query(..., alias="type"),
    author_id: uuid.UUID | None = Query(None, alias="author"),
    category_id: uuid.UUID | None = Query(None, alias="category"),
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Content)
        .options(selectinload(Content.categories), selectinload(Content.author_rel))
        .where(Content.type == content_type)
    )

    if author_id:
        query = query.where(Content.author_id == author_id)

    if category_id:
        query = query.join(Content.categories).where(Category.id == category_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.outerjoin(Author).where(
            or_(
                Author.name.ilike(term),
                Content.slug.ilike(term),
                Content.title.ilike(term),
                Content.summary.ilike(term),
            )
        )

    result = await db.execute(query.distinct().order_by(Content.created_at.desc()).offset(skip).limit(limit))

    return result.scalars().all()


@router.get("/{identifier}", response_model=ContentRead)
async def get_content(
    identifier: str,
    content_type: ContentType = Query(..., alias="type"),
    lookup_field: LookupField = Query(LookupField.UUID),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Content)
        .options(selectinload(Content.categories), selectinload(Content.author_rel))
        .where(Content.type == content_type)
    )

    if lookup_field == LookupField.UUID:
        try:
            target_id = uuid.UUID(identifier)
            query = query.where(Content.id == target_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")
    else:
        query = query.where(Content.slug == identifier)

    result = await db.execute(query)
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    return content


@router.put("/{content_id}", response_model=ContentRead)
async def update_content(
    content_id: uuid.UUID,
    content_data: ContentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Content).options(selectinload(Content.categories)).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    update_data = content_data.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != content.slug:
        existing = await db.execute(select(Content).where(Content.slug == update_data["slug"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A content item with this slug already exists",
            )

    category_ids = update_data.pop("category_ids", None)
    if category_ids is not None:
        content.categories = await get_categories_by_ids(category_ids, db)

    for field, value in update_data.items():
        setattr(content, field, value)

    await db.commit()

    updated = await db.execute(
        select(Content)
        .options(selectinload(Content.categories), selectinload(Content.author_rel))
        .where(Content.id == content.id)
    )
    return updated.scalar_one()


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(content_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    # Automatically delete associated images from R2
    from app.config import get_settings

    settings = get_settings()
    if settings.R2_BUCKET_NAME:
        image_keys = extract_all_content_images(content, settings)
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
                logger.error(f"Failed to delete images from R2 for content {content_id}: {e}")

    await db.delete(content)
    await db.commit()

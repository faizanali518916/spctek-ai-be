import re
import uuid
from datetime import datetime
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.author import Author
from app.models.automation_workflow import AutomationWorkflow
from app.models.contact import ContactSubmission
from app.models.content import Content
from app.models.metadeck import Metadeck
from app.models.popup import Popup

settings = get_settings()
router = APIRouter(tags=["R2 Uploads"])

IMAGE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}


class UploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=1)


class UploadUrlResponse(BaseModel):
    upload_url: str
    key: str
    public_url: str | None = None


class R2BucketImage(BaseModel):
    key: str
    size: int
    last_modified: datetime | None = None
    public_url: str | None = None


class R2UsedImage(BaseModel):
    key: str
    url: str
    source: str
    record_id: uuid.UUID
    field: str


class R2ImageAuditSummary(BaseModel):
    total: int
    used: int
    orphans: int
    author_thumbnails: int
    content_thumbnails: int
    automation_thumbnails: int
    content_items: dict[str, int]


class R2ImageAuditResponse(BaseModel):
    summary: R2ImageAuditSummary
    bucket_images: list[R2BucketImage]
    used_images: list[R2UsedImage]
    orphaned_images: list[R2BucketImage]
    counts: dict[str, int]


class R2OrphanDeleteResponse(BaseModel):
    summary: R2ImageAuditSummary
    deleted: int
    deleted_images: list[R2BucketImage]
    errors: list[dict[str, str]] = Field(default_factory=list)


@lru_cache()
def get_r2_client():
    endpoint = (settings.R2_S3_API_ENDPOINT or "").strip()
    if not endpoint:
        endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    return boto3.client(
        "s3",
        region_name="auto",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


def sanitize_filename(filename: str) -> str:
    cleaned = filename.lower().strip()
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    cleaned = cleaned.strip("-.")
    return cleaned or "upload"


def is_image_key(key: str) -> bool:
    lowered = key.lower()
    return any(lowered.endswith(extension) for extension in IMAGE_EXTENSIONS)


def build_public_url(key: str) -> str | None:
    if not settings.R2_PUBLIC_BASE_URL:
        return None

    public_base = settings.R2_PUBLIC_BASE_URL.rstrip("/")
    if public_base.endswith(".r2.cloudflarestorage.com"):
        return f"{public_base}/{settings.R2_BUCKET_NAME}/{key.lstrip('/')}"

    return f"{public_base}/{key.lstrip('/')}"


def extract_r2_key(url: str) -> str | None:
    if not url:
        return None

    public_base = (settings.R2_PUBLIC_BASE_URL or "").rstrip("/")
    if public_base and url.startswith(public_base):
        remaining = url[len(public_base) :].lstrip("/")
        bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
        if remaining.startswith(bucket_prefix):
            return clean_key(remaining[len(bucket_prefix) :])
        return clean_key(remaining)

    endpoint = (settings.R2_S3_API_ENDPOINT or "").rstrip("/")
    if not endpoint:
        endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    if url.startswith(endpoint):
        remaining = url[len(endpoint) :].lstrip("/")
        bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
        if remaining.startswith(bucket_prefix):
            return clean_key(remaining[len(bucket_prefix) :])

    return None


def extract_image_urls(value: Any) -> list[str]:
    urls: list[str] = []

    if isinstance(value, str):
        urls.extend(re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', value))
        urls.extend(re.findall(r"https?://[^\s\"'<>]+", value, re.IGNORECASE))
        return list(dict.fromkeys(urls))

    if isinstance(value, dict):
        for item in value.values():
            urls.extend(extract_image_urls(item))
        return list(dict.fromkeys(urls))

    if isinstance(value, list):
        for item in value:
            urls.extend(extract_image_urls(item))
        return list(dict.fromkeys(urls))

    return urls


def add_used_image(
    used_images: list[R2UsedImage],
    url: str | None,
    source: str,
    record_id: uuid.UUID,
    field: str,
) -> None:
    if not url:
        return

    key = extract_r2_key(url)
    if key:
        used_images.append(
            R2UsedImage(
                key=key,
                url=url,
                source=source,
                record_id=record_id,
                field=field,
            )
        )


def add_used_images_from_urls(
    used_images: list[R2UsedImage],
    urls: list[str],
    source: str,
    record_id: uuid.UUID,
    field: str,
) -> int:
    count = 0
    for url in urls:
        before = len(used_images)
        add_used_image(used_images, url, source, record_id, field)
        if len(used_images) > before:
            count += 1
    return count


def list_bucket_images() -> list[R2BucketImage]:
    if not settings.R2_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="R2_BUCKET_NAME environment variable not set",
        )

    client = get_r2_client()
    images: list[R2BucketImage] = []
    paginator = client.get_paginator("list_objects_v2")

    try:
        for page in paginator.paginate(Bucket=settings.R2_BUCKET_NAME):
            for item in page.get("Contents", []):
                key = item["Key"]
                if not is_image_key(key):
                    continue

                images.append(
                    R2BucketImage(
                        key=key,
                        size=item.get("Size", 0),
                        last_modified=item.get("LastModified"),
                        public_url=build_public_url(key),
                    )
                )
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list R2 bucket images: {e}",
        )

    return images


def clean_key(key: str) -> str:
    return key.split("?", 1)[0].split("#", 1)[0]


async def collect_used_images(db: AsyncSession) -> tuple[list[R2UsedImage], int, int, int, dict[str, int]]:
    used_images: list[R2UsedImage] = []
    author_thumbnails = 0
    content_thumbnails = 0
    automation_thumbnails = 0
    content_items: dict[str, int] = {}

    content_result = await db.execute(select(Content))
    for content in content_result.scalars().all():
        before = len(used_images)
        add_used_image(used_images, content.thumbnail_url, "content", content.id, "thumbnail_url")
        if len(used_images) > before:
            content_thumbnails += 1

        content_image_count = add_used_images_from_urls(
            used_images,
            extract_image_urls(content.content),
            "content",
            content.id,
            "content",
        )
        content_image_count += add_used_images_from_urls(
            used_images,
            extract_image_urls(content.meta_tags),
            "content",
            content.id,
            "meta_tags",
        )
        content_image_count += add_used_images_from_urls(
            used_images,
            extract_image_urls(content.kpis),
            "content",
            content.id,
            "kpis",
        )
        content_items[str(content.id)] = content_image_count

    author_result = await db.execute(select(Author))
    for author in author_result.scalars().all():
        before = len(used_images)
        add_used_image(used_images, author.profile_picture_url, "author", author.id, "profile_picture_url")
        if len(used_images) > before:
            author_thumbnails += 1
        add_used_images_from_urls(used_images, extract_image_urls(author.about), "author", author.id, "about")
        add_used_images_from_urls(
            used_images,
            extract_image_urls(author.social_links),
            "author",
            author.id,
            "social_links",
        )

    workflow_result = await db.execute(select(AutomationWorkflow))
    for workflow in workflow_result.scalars().all():
        before = len(used_images)
        add_used_image(
            used_images,
            workflow.thumbnail_url,
            "automation_workflow",
            workflow.id,
            "thumbnail_url",
        )
        if len(used_images) > before:
            automation_thumbnails += 1

        add_used_images_from_urls(
            used_images,
            extract_image_urls(workflow.description),
            "automation_workflow",
            workflow.id,
            "description",
        )
        add_used_images_from_urls(
            used_images,
            extract_image_urls(workflow.link),
            "automation_workflow",
            workflow.id,
            "link",
        )

    popup_result = await db.execute(select(Popup))
    for popup in popup_result.scalars().all():
        add_used_images_from_urls(used_images, extract_image_urls(popup.content), "popup", popup.id, "content")

    metadeck_result = await db.execute(select(Metadeck))
    for metadeck in metadeck_result.scalars().all():
        add_used_images_from_urls(used_images, extract_image_urls(metadeck.description), "metadeck", metadeck.id, "description")

    submission_result = await db.execute(select(ContactSubmission))
    for submission in submission_result.scalars().all():
        add_used_images_from_urls(
            used_images,
            extract_image_urls(submission.message),
            "contact_submission",
            submission.id,
            "message",
        )
        add_used_images_from_urls(
            used_images,
            extract_image_urls(submission.journey),
            "contact_submission",
            submission.id,
            "journey",
        )

    return used_images, author_thumbnails, content_thumbnails, automation_thumbnails, content_items


async def build_image_audit(db: AsyncSession) -> R2ImageAuditResponse:
    bucket_images = list_bucket_images()
    used_images, author_thumbnails, content_thumbnails, automation_thumbnails, content_items = (
        await collect_used_images(db)
    )
    used_keys = {image.key for image in used_images}
    orphaned_images = [image for image in bucket_images if image.key not in used_keys]
    summary = R2ImageAuditSummary(
        total=len(bucket_images),
        used=len(used_keys),
        orphans=len(orphaned_images),
        author_thumbnails=author_thumbnails,
        content_thumbnails=content_thumbnails,
        automation_thumbnails=automation_thumbnails,
        content_items=content_items,
    )

    return R2ImageAuditResponse(
        summary=summary,
        bucket_images=bucket_images,
        used_images=used_images,
        orphaned_images=orphaned_images,
        counts={
            "bucket_images": len(bucket_images),
            "used_images": len(used_images),
            "used_unique_images": len(used_keys),
            "orphaned_images": len(orphaned_images),
        },
    )


@router.post("/get-upload-url", response_model=UploadUrlResponse)
async def get_upload_url(payload: UploadUrlRequest):
    if not settings.R2_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="R2_BUCKET_NAME environment variable not set",
        )

    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="R2 credentials are not configured",
        )

    content_type = payload.content_type.strip()
    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content_type is required",
        )

    safe_name = sanitize_filename(payload.filename)
    key = f"uploads/{uuid.uuid4()}-{safe_name}"

    client = get_r2_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=60 * 10,
    )

    public_url = None
    if settings.R2_PUBLIC_BASE_URL:
        public_base = settings.R2_PUBLIC_BASE_URL.rstrip("/")

        # Cloudflare S3 API endpoint URLs need the bucket segment in the path.
        if public_base.endswith(".r2.cloudflarestorage.com"):
            public_url = f"{public_base}/{settings.R2_BUCKET_NAME}/{key.lstrip('/')}"
        else:
            public_url = f"{public_base}/{key.lstrip('/')}"

    return UploadUrlResponse(upload_url=upload_url, key=key, public_url=public_url)


@router.get("/r2/images/audit", response_model=R2ImageAuditResponse)
async def audit_r2_images(db: AsyncSession = Depends(get_db)):
    return await build_image_audit(db)


@router.delete("/r2/images/orphans", response_model=R2OrphanDeleteResponse)
async def delete_orphaned_r2_images(db: AsyncSession = Depends(get_db)):
    audit = await build_image_audit(db)
    used_keys = {image.key for image in audit.used_images}
    bucket_keys = {image.key for image in audit.bucket_images}
    safe_orphans = [
        image
        for image in audit.orphaned_images
        if image.key in bucket_keys and image.key not in used_keys
    ]

    if not safe_orphans:
        return R2OrphanDeleteResponse(
            summary=audit.summary,
            deleted=0,
            deleted_images=[],
            errors=[],
        )

    client = get_r2_client()
    deleted_images: list[R2BucketImage] = []
    errors: list[dict[str, str]] = []

    try:
        for start in range(0, len(safe_orphans), 1000):
            batch = safe_orphans[start : start + 1000]
            response = client.delete_objects(
                Bucket=settings.R2_BUCKET_NAME,
                Delete={
                    "Objects": [{"Key": image.key} for image in batch],
                    "Quiet": False,
                },
            )

            deleted_keys = {item["Key"] for item in response.get("Deleted", [])}
            deleted_images.extend([image for image in batch if image.key in deleted_keys])

            for item in response.get("Errors", []):
                errors.append(
                    {
                        "key": item.get("Key", ""),
                        "code": item.get("Code", ""),
                        "message": item.get("Message", ""),
                    }
                )
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete orphaned R2 images: {e}",
        )

    return R2OrphanDeleteResponse(
        summary=audit.summary,
        deleted=len(deleted_images),
        deleted_images=deleted_images,
        errors=errors,
    )

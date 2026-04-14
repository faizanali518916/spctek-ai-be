import re
import uuid
from functools import lru_cache

import boto3
from botocore.config import Config
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["R2 Uploads"])


class UploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=1)


class UploadUrlResponse(BaseModel):
    upload_url: str
    key: str
    public_url: str | None = None


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

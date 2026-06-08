import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import auth, authors, content, contacts, categories, reinstatement, deploy, r2, metadeck, popups
from app.routers import automation_workflows
from app.services.cache import CachedResponse, cache, cache_get, cache_key

logger = logging.getLogger(__name__)

settings = get_settings()

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


updated_at = os.environ.get("DEPLOYMENT_UPDATED_AT", "Unknown")
description = f"Backend API for SPCTEK AI platform.\n\n**🚀 Last Deployed At:** `{updated_at}`"

app = FastAPI(
    version="1.0.0",
    title="SPCTEK AI API",
    description=description,
    lifespan=lifespan,
)

CORS_ORIGINS = [
    "https://spctek.ai",
    "https://www.spctek.ai",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
)


# Debug middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path} - Origin: {request.headers.get('origin', 'N/A')}")
    try:
        response = await call_next(request)
        logger.info(f"Status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise


@app.middleware("http")
async def cache_responses(request: Request, call_next):
    cacheable_request = (
        request.method == "GET"
        and "authorization" not in request.headers
        and not request.url.path.startswith("/r2/images")
    )
    key = cache_key(request.method, str(request.url))

    if cacheable_request:
        hit, cached = cache_get(key)
        if hit:
            logger.info("Cache HIT: %s %s", request.method, request.url.path)
            headers = dict(cached.headers)
            headers["X-Cache"] = "HIT"
            return Response(
                content=cached.body,
                status_code=cached.status_code,
                media_type=cached.media_type,
                headers=headers,
            )
    else:
        logger.info("Cache BYPASS: %s %s", request.method, request.url.path)

    response = await call_next(request)

    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and 200 <= response.status_code < 400:
        logger.info("Cache INVALIDATED: %s %s", request.method, request.url.path)
        cache.clear()
        return response

    content_type = response.headers.get("content-type", "")
    should_cache_response = (
        cacheable_request
        and response.status_code == 200
        and content_type.startswith("application/json")
        and "set-cookie" not in response.headers
    )
    if not should_cache_response:
        if cacheable_request:
            logger.info("Cache BYPASS: %s %s status=%s", request.method, request.url.path, response.status_code)
        return response

    body = b"".join([chunk async for chunk in response.body_iterator])
    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-length", "content-encoding", "transfer-encoding"}
    }
    media_type = content_type.split(";", 1)[0] if content_type else response.media_type

    cached = CachedResponse(
        body=body,
        status_code=response.status_code,
        media_type=media_type,
        headers=headers,
    )
    cache.set(key, cached)
    logger.info("Cache MISS: %s %s", request.method, request.url.path)

    headers["X-Cache"] = "MISS"
    return Response(
        content=body,
        status_code=response.status_code,
        media_type=media_type,
        headers=headers,
    )


app.include_router(auth.router)
app.include_router(authors.router)
app.include_router(content.router)
app.include_router(contacts.router)
app.include_router(categories.router)
app.include_router(reinstatement.router)
app.include_router(deploy.router)
app.include_router(r2.router)
app.include_router(metadeck.router)
app.include_router(popups.router)
app.include_router(automation_workflows.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "spctek-ai-api"}

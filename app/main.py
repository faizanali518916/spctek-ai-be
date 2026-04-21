import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import content, contacts, reinstatement, auth, categories, deploy, r2

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    version="1.0.4.15",
    title="SPCTEK AI API",
    description="Backend API for SPCTEK AI platform",
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


app.include_router(auth.router)
app.include_router(content.router)
app.include_router(categories.router)
app.include_router(contacts.router)
app.include_router(reinstatement.router)
app.include_router(deploy.router)
app.include_router(r2.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "spctek-ai-api"}

import logging
import ssl
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.config import get_settings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

settings = get_settings()
logger = logging.getLogger(__name__)

ssl_context = None
if "localhost" not in settings.DATABASE_URL and "127.0.0.1" not in settings.DATABASE_URL:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

connect_args = {"timeout": 30}
if ssl_context:
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


RETRYABLE_DB_ERRORS = (OperationalError, DisconnectionError, TimeoutError, OSError)


@retry(
    retry=retry_if_exception_type(RETRYABLE_DB_ERRORS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
    after=lambda retry_state: logger.warning(
        "Database connection attempt %s failed: %s",
        retry_state.attempt_number,
        retry_state.outcome.exception(),
    ),
)
async def wait_for_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin to add id, created_at and updated_at timestamps to models."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_db():
    await wait_for_database()
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    await wait_for_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

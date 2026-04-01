from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings
import ssl

settings = get_settings()

# Configure SSL for asyncpg - only for remote databases
ssl_context = None
if (
    "localhost" not in settings.DATABASE_URL
    and "127.0.0.1" not in settings.DATABASE_URL
):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

# Create async engine with connection pooling
connect_args = {"timeout": 30}
if ssl_context:
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Test connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

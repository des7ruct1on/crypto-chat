from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.postgres_dsn, echo=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def get_session() -> AsyncSession:
    return async_session_factory()

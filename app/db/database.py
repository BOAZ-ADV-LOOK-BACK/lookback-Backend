from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

# PostgreSQL URL
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://lookback_user:pass1234@172.31.19.46/lookback"

# 비동기 엔진 생성
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# 비동기 세션 설정
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base 클래스 생성
Base = declarative_base()

# 비동기 DB 세션 의존성
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
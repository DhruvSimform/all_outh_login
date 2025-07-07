from decouple import config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = config("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

class Base(DeclarativeBase):
    pass


async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with async_session() as session:
        yield session

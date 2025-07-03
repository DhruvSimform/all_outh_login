from decouple import config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = config("DATABASE_URL")

engine = create_engine(
    DATABASE_URL, echo=True, connect_args={"check_same_thread": False}
)

class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(bind=engine)

def get_db():
    with SessionLocal() as db:
        yield db

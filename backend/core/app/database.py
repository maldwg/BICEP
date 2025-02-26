from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
import os 
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from contextlib import asynccontextmanager

database_url = os.environ.get("DATABASE_URL")
database_name = os.environ.get("DATABASE_NAME")
database_user = os.environ.get("DATABASE_USER")
database_password = os.environ.get("DATABASE_PASSWORD")

if all([database_url, database_name, database_user, database_password]):
    SQLALCHEMY_DATABASE_URL = f"mariadb+asyncmy://{database_user}:{database_password}@{database_url}/{database_name}"
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, future=True)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
else:
    SQLALCHEMY_DATABASE_URL = None
    engine = None
    SessionLocal = None
Base = declarative_base()

def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database connection is not configured properly.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_db_session_context():
    """
    Async method to create db connections for use outside of FastAPI dependency injection.
    Ensures that the session is properly closed.
    """
    if SessionLocal is None:
        raise RuntimeError("Database connection is not configured properly.")

    db: AsyncSession = SessionLocal()
    try:
        yield db  
    finally:
        await db.close()  
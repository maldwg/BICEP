from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os 


database_url = os.environ.get("DATABASE_URL")
database_name = os.environ.get("DATABASE_NAME")
database_user = os.environ.get("DATABASE_USER")
database_password = os.environ.get("DATABASE_PASSWORD")

# Gracefully handle missing configuration by providing defaults or skipping connection setup
if all([database_url, database_name, database_user, database_password]):
    SQLALCHEMY_DATABASE_URL = f"mariadb://{database_user}:{database_password}@{database_url}/{database_name}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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

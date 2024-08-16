from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os 


database_url = os.environ.get("DATABASE_URL")
database_name = os.environ.get("DATABASE_NAME")
database_user = os.environ.get("DATABASE_USER")
database_password = os.environ.get("DATABASE_PASSWORD")

SQLALCHEMY_DATABASE_URL = "mariadb://"+ database_user + ":" + database_password + "@" + database_url + "/" + database_name

engine = create_engine(
    SQLALCHEMY_DATABASE_URL # , connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


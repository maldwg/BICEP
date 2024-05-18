from .database import SessionLocal

def test():
    return {"test"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# URL com senha escapada (@ vira %40)
DATABASE_URL = "postgresql://safedrive_user:Vasco%40123@localhost:5432/safedrive"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

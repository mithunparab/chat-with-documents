from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """
    Initializes the database by creating all tables.
    In a production environment, you would use Alembic for migrations.
    """
    print("Initializing database and creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

def get_db():
    """
    FastAPI dependency to get a database session.
    Ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
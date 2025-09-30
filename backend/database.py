from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def init_db():
    # Import all models to ensure they're registered with Base
    from models.chat import ChatHistory, UserSession
    from models.session import ChatSession
    from models.creative import AdCreative, CreativeInsight
    from models.user_profile import UserProfile, AuthSession, UserActivity, AccountMapping
    Base.metadata.create_all(bind=engine)
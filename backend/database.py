"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from models import Base
import os


class DatabaseManager:
    """Manage database connection and sessions"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            poolclass=NullPool if "sqlite" in database_url else None,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    async def init_db(self):
        """Initialize database tables"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()


def get_db():
    """Dependency for FastAPI to get database session"""
    db_url = os.getenv("DATABASE_URL", "postgresql://carepulse:carepulse@localhost/carepulse")
    manager = DatabaseManager(db_url)
    db = manager.get_session()
    try:
        yield db
    finally:
        db.close()

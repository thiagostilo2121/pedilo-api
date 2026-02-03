from sqlmodel import SQLModel, create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

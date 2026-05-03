import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import ROOT, load_env


load_env()


def get_database_url() -> str:
    default_path = ROOT / ".data" / "gemma_glot.db"
    return os.getenv("DATABASE_URL", f"sqlite:///{default_path}")


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


DATABASE_URL = get_database_url()
if DATABASE_URL.startswith("sqlite"):
    Path(DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args(DATABASE_URL),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from backend.app import models

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

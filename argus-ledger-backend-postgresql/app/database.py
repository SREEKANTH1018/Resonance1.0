"""SQLAlchemy engine, session factory and declarative base.

The engine URL is resolved once from :func:`app.config.get_settings`. Request
handlers depend on :func:`get_db`, which yields a session and always closes it.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.sql_echo,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Deterministic constraint/index names keep future Alembic migrations sane.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session, guarantee it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

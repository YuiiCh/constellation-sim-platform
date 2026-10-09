"""SQLAlchemy 引擎与会话管理。SQLite 持久化所有仿真相关数据。"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import Settings


class Base(DeclarativeBase):
    pass


_settings = Settings()
_engine = create_engine(
    f"sqlite:///{_settings.SQLITE_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI 依赖：提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建全部表（幂等）。"""
    # 导入模型以确保注册到 Base.metadata
    from . import models  # noqa: F401

    Base.metadata.create_all(_engine)


def get_engine():
    return _engine

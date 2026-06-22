from typing import Generator

from job_agent.db.session import SessionLocal


def get_db() -> Generator:
    """FastAPI 依赖：提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 数据库文件路径：项目根目录下的 data/job_agent.db
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "job_agent.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """获取一个新的数据库会话"""
    return SessionLocal()


def ensure_db_dir():
    """确保数据库目录存在"""
    os.makedirs(DB_DIR, exist_ok=True)

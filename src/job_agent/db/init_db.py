from job_agent.db.models import Base
from job_agent.db.session import ensure_db_dir, engine


def init_db():
    """初始化数据库，创建所有表"""
    ensure_db_dir()
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成，所有表已创建。")


if __name__ == "__main__":
    init_db()

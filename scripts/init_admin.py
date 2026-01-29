import os
import sys

# 将项目根目录添加到 python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from app.db.sqlite import sqlite_db
from app.core.auth import get_password_hash
from app.core.logger import setup_logging
import logging

def init_admin():
    """
    初始化默认管理员账号 (admin/admin)
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    username = "admin"
    password = "admin"
    
    logger.info(f"正在检查管理员账号: {username}")
    
    existing_user = sqlite_db.get_user_by_username(username)
    if not existing_user:
        password_hash = get_password_hash(password)
        sqlite_db.create_user(
            username=username,
            password_hash=password_hash,
            role="admin"
        )
        logger.info(f"成功创建默认管理员账号: {username} / {password}")
    else:
        logger.info(f"管理员账号 {username} 已存在，跳过初始化。")

if __name__ == "__main__":
    init_admin()

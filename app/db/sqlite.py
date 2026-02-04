"""
SQLite 数据库管理模块

用于存储系统配置等轻量级数据，替代 MongoDB 存储配置信息
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

class SQLiteDB:
    """SQLite 数据库管理类"""
    
    _instance = None
    _db_path = "data/configs.db"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    def __init__(self):
        self._ensure_data_dir()
        self._init_db()
        
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 创建配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS configs (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP
        )
        ''')

        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, role, created_at, updated_at FROM users')
        rows = cursor.fetchall()
        
        users = []
        for row in rows:
            users.append({
                "id": row['id'],
                "username": row['username'],
                "role": row['role'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            })
        conn.close()
        return users

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def create_user(self, username: str, password_hash: str, role: str = 'admin') -> int:
        """创建用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            'INSERT INTO users (username, password, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
            (username, password_hash, role, now, now)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id

    def update_user(self, user_id: int, username: str = None, password_hash: str = None, role: str = None) -> bool:
        """更新用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        updates = []
        params = []
        if username:
            updates.append("username = ?")
            params.append(username)
        if password_hash:
            updates.append("password = ?")
            params.append(password_hash)
        if role:
            updates.append("role = ?")
            params.append(role)
            
        if not updates:
            return False
            
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates.append("updated_at = ?")
        params.append(now)
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
        
    def get_all_configs(self) -> List[Dict[str, Any]]:
        """获取所有配置"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM configs')
        rows = cursor.fetchall()
        
        configs = []
        for row in rows:
            configs.append({
                "key": row['key'],
                "value": row['value'], # 这里假设 value 是字符串，如果前端需要 JSON 对象，可能需要转换，但 ConfigModel 中 value 是 Any。
                                      # 在 Mongo 中它是直接存的。为了兼容，我们把 value 当字符串存。
                                      # 如果 value 本身是复杂对象，应该序列化。
                                      # 简单起见，我们统一将 value 作为字符串存储，如果需要 JSON，调用者自己解析。
                                      # 但看 ConfigModel value 是 Any，且 admin.py update_config 传的是 dict (value.get("value"))。
                                      # 让我们看看 create_config，它接收 ConfigModel。
                                      # 如果 ConfigModel.value 是 dict/list，存入 SQLite 需要 json.dumps。
                                      # 取出时需要 json.loads。
                "description": row['description'],
                "updated_at": row['updated_at']
            })
        conn.close()
        return configs

    def get_config(self, key: str) -> Optional[Dict[str, Any]]:
        """获取指定配置"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM configs WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "key": row['key'],
                "value": row['value'],
                "description": row['description'],
                "updated_at": row['updated_at']
            }
        return None
        
    def set_config(self, key: str, value: Any, description: str = None):
        """设置配置（新增或更新）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 使用本地时间
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否存在
        cursor.execute('SELECT 1 FROM configs WHERE key = ?', (key,))
        exists = cursor.fetchone()
        
        # 确保 value 是字符串
        if not isinstance(value, str):
             # 尝试转 JSON 字符串，如果 value 是 dict/list
             try:
                 value = json.dumps(value, ensure_ascii=False)
             except:
                 value = str(value)
        
        if exists:
            if description is not None:
                cursor.execute(
                    'UPDATE configs SET value = ?, description = ?, updated_at = ? WHERE key = ?',
                    (value, description, updated_at, key)
                )
            else:
                cursor.execute(
                    'UPDATE configs SET value = ?, updated_at = ? WHERE key = ?',
                    (value, updated_at, key)
                )
        else:
            cursor.execute(
                'INSERT INTO configs (key, value, description, updated_at) VALUES (?, ?, ?, ?)',
                (key, value, description, updated_at)
            )
            
        conn.commit()
        conn.close()
        
    def delete_config(self, key: str) -> bool:
        """删除配置"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM configs WHERE key = ?', (key,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

# 全局 SQLite 实例
sqlite_db = SQLiteDB()

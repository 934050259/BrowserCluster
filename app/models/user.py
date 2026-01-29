from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    role: str = "admin"  # 默认为 admin

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class UserInDB(UserBase):
    id: int
    hashed_password: str
    created_at: str
    updated_at: str

class UserResponse(UserBase):
    id: int
    created_at: str
    updated_at: str

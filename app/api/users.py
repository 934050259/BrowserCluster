from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.auth import get_current_admin, get_password_hash
from app.db.sqlite import sqlite_db
from app.models.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/", response_model=List[UserResponse])
async def get_users(current_admin: dict = Depends(get_current_admin)):
    """获取所有用户 (仅限管理员)"""
    return sqlite_db.get_all_users()

@router.post("/", response_model=UserResponse)
async def create_user(user_in: UserCreate, current_admin: dict = Depends(get_current_admin)):
    """创建用户 (仅限管理员)"""
    # 检查用户是否已存在
    existing_user = sqlite_db.get_user_by_username(user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system."
        )
    
    password_hash = get_password_hash(user_in.password)
    user_id = sqlite_db.create_user(
        username=user_in.username,
        password_hash=password_hash,
        role=user_in.role
    )
    
    new_user = sqlite_db.get_user_by_id(user_id)
    return new_user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_in: UserUpdate, current_admin: dict = Depends(get_current_admin)):
    """更新用户 (仅限管理员)"""
    user = sqlite_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user with this id does not exist in the system."
        )
    
    password_hash = None
    if user_in.password:
        password_hash = get_password_hash(user_in.password)
    
    sqlite_db.update_user(
        user_id=user_id,
        username=user_in.username,
        password_hash=password_hash,
        role=user_in.role
    )
    
    updated_user = sqlite_db.get_user_by_id(user_id)
    return updated_user

@router.delete("/{user_id}")
async def delete_user(user_id: int, current_admin: dict = Depends(get_current_admin)):
    """删除用户 (仅限管理员)"""
    user = sqlite_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user with this id does not exist in the system."
        )
    
    # 防止删除自己
    if user["username"] == current_admin["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot delete themselves."
        )
        
    sqlite_db.delete_user(user_id)
    return {"status": "success"}

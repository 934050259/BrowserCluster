from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.core.auth import verify_password, create_access_token, get_current_user
from app.db.sqlite import sqlite_db
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录接口"""
    user = sqlite_db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }
    }

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"]
    }

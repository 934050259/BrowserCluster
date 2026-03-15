from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from app.models.cookie import (
    Cookie, CookieCreate, CookieUpdate, CookieFilter, 
    CookieStats, CookieConfig, CookieListResponse
)
from app.services.cookie_service import cookie_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/v1/cookies", tags=["Cookie Pool"])

@router.post("/", response_model=Cookie)
async def create_cookie(cookie: CookieCreate, current_user=Depends(get_current_user)):
    """添加 Cookie"""
    return await cookie_service.add_cookie(cookie)

@router.get("/", response_model=CookieListResponse)
async def list_cookies(
    domain: Optional[str] = None,
    group: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user)
):
    """获取 Cookie 列表"""
    filter_data = CookieFilter(domain=domain, group=group, status=status)
    return await cookie_service.list_cookies(filter_data, skip=skip, limit=limit)

@router.get("/best", response_model=Cookie)
async def get_best_cookie(domain: str, group: str = "default"):
    """
    获取最佳可用 Cookie (考虑频率限制)
    注意：此接口不需要鉴权，供内部服务调用
    """
    cookie = await cookie_service.get_best_cookie(domain, group)
    if not cookie:
        raise HTTPException(status_code=404, detail="No available cookie found")
    return cookie

@router.get("/stats", response_model=CookieStats)
async def get_cookie_stats(current_user=Depends(get_current_user)):
    """获取 Cookie 池统计信息"""
    return await cookie_service.get_stats()

@router.get("/config", response_model=CookieConfig)
async def get_cookie_config(current_user=Depends(get_current_user)):
    """获取 Cookie 检测配置"""
    return await cookie_service.get_config()

@router.put("/config")
async def update_cookie_config(config: CookieConfig, current_user=Depends(get_current_user)):
    """更新 Cookie 检测配置"""
    success = await cookie_service.update_config(config)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update cookie configuration")
    return {"message": "Cookie configuration updated successfully"}

@router.get("/export-all", response_model=List[CookieCreate])
async def export_cookies(current_user=Depends(get_current_user)):
    """导出所有 Cookie"""
    return await cookie_service.bulk_export()

@router.get("/{cookie_id}", response_model=Cookie)
async def get_cookie(cookie_id: str, current_user=Depends(get_current_user)):
    """获取 Cookie 详情"""
    # 由于 cookie_id 可能包含特殊字符（如 :），确保 URL 编码正确
    # 这里直接接收 path parameter，FastAPI 会处理
    cookie = await cookie_service.get_cookie_by_id(cookie_id)
    if not cookie:
        raise HTTPException(status_code=404, detail="Cookie not found")
    return cookie

@router.put("/{cookie_id}", response_model=Cookie)
async def update_cookie(cookie_id: str, update: CookieUpdate, current_user=Depends(get_current_user)):
    """更新 Cookie 信息"""
    cookie = await cookie_service.update_cookie(cookie_id, update)
    if not cookie:
        raise HTTPException(status_code=404, detail="Cookie not found")
    return cookie

@router.delete("/{cookie_id}")
async def delete_cookie(cookie_id: str, current_user=Depends(get_current_user)):
    """删除 Cookie"""
    success = await cookie_service.delete_cookie(cookie_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cookie not found")
    return {"message": "Cookie deleted successfully"}

@router.post("/batch-delete")
async def batch_delete_cookies(cookie_ids: List[str] = Body(...), current_user=Depends(get_current_user)):
    """批量删除 Cookie"""
    count = await cookie_service.bulk_delete_cookies(cookie_ids)
    return {"message": f"Successfully deleted {count} cookies"}

@router.post("/import")
async def import_cookies(cookies: List[CookieCreate], current_user=Depends(get_current_user)):
    """批量导入 Cookie"""
    count = await cookie_service.bulk_import(cookies)
    return {"message": f"Successfully imported {count} cookies"}

@router.post("/check-all")
async def check_all_cookies(current_user=Depends(get_current_user)):
    """检测所有 Cookie"""
    # 异步执行，不等待结果
    # 注意：这里应该放到后台任务中，或者直接 fire-and-forget
    # 为了简单起见，这里等待结果，或者可以改为 BackgroundTasks
    # 考虑到可能很慢，建议使用 BackgroundTasks
    # 但这里先简单的 await
    await cookie_service.check_all_cookies()
    return {"message": "Finished checking all cookies"}

@router.post("/{cookie_id}/check")
async def check_single_cookie(cookie_id: str, current_user=Depends(get_current_user)):
    """检测单个 Cookie"""
    cookie = await cookie_service.get_cookie_by_id(cookie_id)
    if not cookie:
        raise HTTPException(status_code=404, detail="Cookie not found")
    is_active = await cookie_service.check_cookie(cookie)
    return {"active": is_active, "status": cookie.status}

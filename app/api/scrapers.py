from typing import List
import asyncio
import logging
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from app.models.scraper import ScraperCreate, ScraperUpdate, ScraperResponse, ScraperTestRequest, AIExtractRequest
from app.db.mongo import mongo
from app.core.auth import get_current_user
from app.core.scraper import Scraper
from app.core.scheduler import scraper_scheduler
from app.services.scraper_service import execute_scraper_task
from app.services.task_service import task_service
from app.services.parser_service import parser_service
from app.models.task import ScrapeRequest, ScrapeParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scrapers", tags=["Scrapers"])

@router.get("/", response_model=List[ScraperResponse])
async def get_scrapers(current_user: dict = Depends(get_current_user)):
    scrapers = list(mongo.db.scrapers.find().sort("created_at", -1))
    return scrapers

@router.post("/", response_model=ScraperResponse)
async def create_scraper(scraper: ScraperCreate, current_user: dict = Depends(get_current_user)):
    doc = scraper.model_dump()
    # Convert HttpUrl to string for MongoDB compatibility
    if doc.get("url"):
        doc["url"] = str(doc["url"])
        
    doc["created_at"] = datetime.now()
    doc["updated_at"] = datetime.now()
    result = mongo.db.scrapers.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    # 如果启用了定时任务，添加到调度器
    if doc.get("enabled_schedule") and doc.get("cron"):
        scraper_scheduler.add_or_update_job(doc)
        
    return doc

@router.put("/{scraper_id}", response_model=ScraperResponse)
async def update_scraper(scraper_id: str, scraper: ScraperUpdate, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(scraper_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    update_data = {k: v for k, v in scraper.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    # Convert HttpUrl to string for MongoDB compatibility
    if update_data.get("url"):
        update_data["url"] = str(update_data["url"])
        
    update_data["updated_at"] = datetime.now()
    
    result = mongo.db.scrapers.find_one_and_update(
        {"_id": ObjectId(scraper_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    # 更新调度器状态
    if result.get("enabled_schedule") and result.get("cron"):
        scraper_scheduler.add_or_update_job(result)
    else:
        scraper_scheduler.remove_job(scraper_id)
        
    return result

@router.delete("/{scraper_id}")
async def delete_scraper(scraper_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(scraper_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    result = mongo.db.scrapers.delete_one({"_id": ObjectId(scraper_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    # 从调度器中移除
    scraper_scheduler.remove_job(scraper_id)
        
    return {"status": "success"}

@router.post("/test", response_model=dict)
async def test_scraper(request: ScraperTestRequest, current_user: dict = Depends(get_current_user)):
    try:
        scraper = Scraper()
        
        # 使用统一的 scrape_list 方法
        result = await scraper.scrape_list(
            url=str(request.url),
            list_xpath=request.list_xpath,
            title_xpath=request.title_xpath,
            link_xpath=request.link_xpath,
            time_xpath=request.time_xpath,
            params={
                "engine": request.engine,
                "wait_for": request.wait_for,
                "wait_time": request.wait_time,
                "wait_for_selector": request.wait_for_selector,
                "wait_timeout": request.wait_timeout,
                "block_images": request.block_images,
                "no_css": request.no_css,
                "stealth": request.stealth,
                "max_retries": request.max_retries,
                "proxy": request.proxy,
                "proxy_pool_group": request.proxy_pool_group,
                "cookies": request.cookies
            }
        )
        
        if result.get("status") == "failed":
            raise Exception(result.get("error"))
            
        return {
            "status": "success",
            "html": result.get("html"), 
            "items": result.get("items", [])[:20], # Limit items for preview
            "count": result.get("count", 0)
        }
    except Exception as e:
        logger.error(f"Scraper test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai-extract", response_model=dict)
async def ai_extract_xpath(request: AIExtractRequest, current_user: dict = Depends(get_current_user)):
    """调用 AI 智能解析获取 XPath 规则"""
    try:
        scraper = Scraper()
        
        # 1. 先抓取页面 HTML
        res = await scraper.scrape(
            url=str(request.url),
            params={
                "engine": request.engine,
                "wait_for": request.wait_for,
                "wait_time": request.wait_time,
                "wait_for_selector": request.wait_for_selector,
                "wait_timeout": request.wait_timeout,
                "block_images": request.block_images,
                "no_css": request.no_css,
                "stealth": request.stealth,
                "proxy": request.proxy,
                "proxy_pool_group": request.proxy_pool_group,
                "cookies": request.cookies,
                "user_agent": request.user_agent
            },
            node_id="internal"
        )
        
        if res.get("status") != "success":
            raise Exception(f"页面抓取失败: {res.get('error')}")
            
        html = res.get("html")
        if not html:
            raise Exception("未获取到页面 HTML")
            
        # 2. 调用 ParserService 的 AI 功能
        ai_result = await parser_service.parse(
            html=html,
            parser_type="llm",
            config={"mode": "xpath_helper"}
        )
        
        if "error" in ai_result:
            raise Exception(ai_result["error"])
            
        return {
            "status": "success",
            "data": ai_result
        }
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{scraper_id}/run")
async def run_scraper(scraper_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(scraper_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    scraper_doc = mongo.db.scrapers.find_one({"_id": ObjectId(scraper_id)})
    if not scraper_doc:
        raise HTTPException(status_code=404, detail="Scraper not found")
        
    # 检查站点是否启用
    if not scraper_doc.get("enabled", True):
        raise HTTPException(status_code=400, detail="该站点已禁用，无法执行采集")
        
    # 后台执行采集任务
    asyncio.create_task(execute_scraper_task(scraper_doc))
    
    return {"status": "success", "message": "Scraper task started in background"}

# 移除了 execute_scraper_task，已移动到 app.services.scraper_service

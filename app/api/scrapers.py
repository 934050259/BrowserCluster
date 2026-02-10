from fastapi import APIRouter, HTTPException, Depends, status, Body
from typing import List
from app.models.scraper import ScraperCreate, ScraperUpdate, ScraperResponse, ScraperTestRequest
from app.db.mongo import mongo
import logging
from app.core.auth import get_current_user
from bson import ObjectId
from datetime import datetime
from app.core.scraper import Scraper
from lxml import html as lxml_html
from urllib.parse import urljoin

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
        
    return result

@router.delete("/{scraper_id}")
async def delete_scraper(scraper_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(scraper_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    result = mongo.db.scrapers.delete_one({"_id": ObjectId(scraper_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scraper not found")
        
    return {"status": "success"}

@router.post("/test", response_model=dict)
async def test_scraper(request: ScraperTestRequest, current_user: dict = Depends(get_current_user)):
    try:
        scraper = Scraper()
        
        # 使用统一的 scrape_list 方法，内部已包含 urljoin 逻辑
        result = await scraper.scrape_list(
            url=str(request.url),
            list_xpath=request.list_xpath,
            title_xpath=request.title_xpath,
            link_xpath=request.link_xpath,
            time_xpath=request.time_xpath,
            params={
                "wait_for_selector": request.wait_for_selector,
                "wait_timeout": request.wait_timeout,
                "no_images": request.no_images,
                "no_css": request.no_css,
                "engine": "drissionpage" # 校验规则默认使用 dp
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
        logger.error(f"Test scrape failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

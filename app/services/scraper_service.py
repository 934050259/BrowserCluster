import logging
from bson import ObjectId
from app.db.mongo import mongo
from app.core.scraper import Scraper
from app.services.task_service import task_service
from app.models.task import ScrapeRequest, ScrapeParams

logger = logging.getLogger(__name__)

async def execute_scraper_task(scraper_doc: dict):
    """后台执行站点采集任务"""
    try:
        scraper_id = str(scraper_doc["_id"])
        scraper_name = scraper_doc["name"]
        
        # 检查站点是否启用
        if not scraper_doc.get("enabled", True):
            logger.info(f"Scraper task skipped (disabled): {scraper_name} ({scraper_id})")
            return
            
        logger.info(f"Starting scraper task: {scraper_name} ({scraper_id})")
        
        scraper = Scraper()
        
        # 1. 抓取列表页并提取项
        params_config = scraper_doc.get("params", {})
        
        # 兼容旧数据，如果 params 为空则从顶级获取
        def get_val(key, default=None):
            return params_config.get(key, scraper_doc.get(key, default))

        result = await scraper.scrape_list(
            url=scraper_doc["url"],
            list_xpath=scraper_doc["list_xpath"],
            title_xpath=scraper_doc["title_xpath"],
            link_xpath=scraper_doc["link_xpath"],
            time_xpath=scraper_doc.get("time_xpath"),
            params={
                "engine": get_val("engine", "playwright"),
                "wait_for": get_val("wait_for", "networkidle"),
                "wait_time": get_val("wait_time", 3000),
                "wait_timeout": get_val("timeout", scraper_doc.get("wait_timeout", 30000)),
                "wait_for_selector": get_val("wait_for_selector"),
                "viewport": get_val("viewport"),
                "stealth": get_val("stealth", True),
                "no_images": get_val("no_images", True),
                "no_css": get_val("no_css", True),
                "block_images": get_val("block_images", False),
                "block_media": get_val("block_media", False),
                "proxy": get_val("proxy"),
                "proxy_pool_group": get_val("proxy_pool_group"),
                "cookies": get_val("cookies"),
                "intercept_apis": get_val("intercept_apis"),
                "intercept_continue": get_val("intercept_continue", False),
                "max_pages": scraper_doc.get("max_pages", 1),
                "max_retries": scraper_doc.get("max_retries", 2),
                "pagination_next_xpath": scraper_doc.get("pagination_next_xpath")
            }
        )
        
        if result.get("status") == "failed":
            logger.error(f"Scraper task failed: {result.get('error')}")
            return
            
        items = result.get("items", [])
        logger.info(f"Extracted {len(items)} items from {scraper_doc['url']}")
        
        # 2. 获取规则信息（如果关联了规则）
        rule_id = scraper_doc.get("rule_id")
        rule_doc = None
        if rule_id:
            try:
                # 兼容不同 ID 类型
                query = {}
                if ObjectId.is_valid(rule_id):
                    query["_id"] = ObjectId(rule_id)
                else:
                    query["id"] = rule_id
                
                rule_doc = mongo.db.parsing_rules.find_one(query)
            except Exception as e:
                logger.warning(f"Failed to fetch rule {rule_id}: {e}")
        
        # 3. 为每个提取到的链接创建采集任务
        count = 0
        for item in items:
            link = item.get("link")
            if not link:
                continue
                
            # 构造抓取参数
            params = ScrapeParams(
                engine=get_val("engine", "playwright"),
                wait_for=get_val("wait_for", "networkidle"),
                wait_time=get_val("wait_time", 3000),
                timeout=get_val("timeout", scraper_doc.get("wait_timeout", 30000)),
                viewport=get_val("viewport", {"width": 1920, "height": 1080}),
                stealth=get_val("stealth", True),
                block_images=get_val("block_images", get_val("no_images", True)),
                block_media=get_val("block_media", False),
                user_agent=get_val("user_agent"),
                proxy=get_val("proxy"),
                proxy_pool_group=get_val("proxy_pool_group"),
                cookies=get_val("cookies"),
                intercept_apis=get_val("intercept_apis"),
                intercept_continue=get_val("intercept_continue", False),
                storage_type=get_val("storage_type", "mongo"),
                mongo_collection=get_val("mongo_collection"),
                oss_path=get_val("oss_path"),
                save_html=get_val("save_html", True),
                screenshot=get_val("screenshot", False),
                is_fullscreen=get_val("is_fullscreen", False),
                max_retries=get_val("max_retries", 2)
            )

            if rule_doc:
                params.parser = rule_doc.get("parser_type")
                params.parser_config = rule_doc.get("parser_config")
                
                # 也可以带入一些默认采集配置
                if rule_doc.get("parser_type") == "gne":
                    # GNE 建议开启渲染
                    params.engine = "playwright"
            
            # 构造抓取请求
            request = ScrapeRequest(
                url=link,
                params=params
            )
            
            # 如果有 schedule_id 或 scraper_id，可以存入 metadata 或 task_data
            # 这里先通过 schedule_id 记录来源
            request.schedule_id = f"scraper_{scraper_id}"
            
            # 创建任务
            await task_service.create_task(request)
            count += 1
            
        logger.info(f"Created {count} detail scraping tasks for scraper: {scraper_name}")
        
    except Exception as e:
        logger.error(f"Error executing scraper task: {e}", exc_info=True)

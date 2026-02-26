import logging
from urllib.parse import urlparse
from datetime import datetime
from bson import ObjectId
from app.db.mongo import mongo
from app.core.scraper import Scraper
from app.services.task_service import task_service
from app.models.task import ScrapeRequest, ScrapeParams

logger = logging.getLogger(__name__)

async def update_scraper_status(scraper_id: str, status: str, error: str = None):
    """更新采集任务测试状态"""
    try:
        update_doc = {
            "last_test_status": status,
            "last_test_at": datetime.now()
        }
        if error is not None:
            update_doc["last_test_error"] = error
        else:
            update_doc["last_test_error"] = ""
            
        mongo.db.scrapers.update_one(
            {"_id": ObjectId(scraper_id)},
            {"$set": update_doc}
        )
    except Exception as e:
        logger.error(f"Failed to update scraper status: {e}")

def _match_rule_by_url(url: str):
    """根据 URL 匹配解析规则"""
    try:
        domain = urlparse(url).netloc
        # 获取所有启用的规则，按优先级排序
        rules = list(mongo.db.parsing_rules.find({"is_active": True}).sort("priority", -1))
        
        for rule in rules:
            rule_domain = rule.get("domain", "")
            if not rule_domain:
                continue
                
            # 1. 精确匹配
            if rule_domain == domain:
                return rule
            
            # 2. 通配符匹配 (如 *.example.com)
            if rule_domain.startswith("*."):
                suffix = rule_domain[1:] # .example.com
                if domain.endswith(suffix):
                    return rule
            
            # 3. 父域名匹配 (如果规则是 example.com，也匹配 sub.example.com)
            if domain.endswith("." + rule_domain):
                return rule
                
    except Exception as e:
        logger.warning(f"Error matching rule for URL {url}: {e}")
    return None

async def execute_scraper_task(scraper_doc: dict):
    """后台执行站点采集任务"""
    scraper_id = str(scraper_doc["_id"])
    scraper_name = scraper_doc["name"]
    
    try:
        # 检查站点是否启用
        if not scraper_doc.get("enabled", True):
            logger.info(f"Scraper task skipped (disabled): {scraper_name} ({scraper_id})")
            return
            
        logger.info(f"Starting scraper task: {scraper_name} ({scraper_id})")
        
        # 更新状态为运行中
        await update_scraper_status(scraper_id, "running")
        
        scraper = Scraper()
        
        # 0. 获取规则信息（仅用于详情页采集任务的继承）
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
        
        # 如果没有明确关联规则，尝试根据 URL 域名自动匹配（仅用于详情页任务）
        if not rule_doc:
            rule_doc = _match_rule_by_url(scraper_doc["url"])
            if rule_doc:
                logger.info(f"Automatically matched rule {rule_doc.get('domain')} for detail tasks of scraper {scraper_name}")
        
        # 1. 抓取列表页并提取项
        params_config = scraper_doc.get("params", {})
        
        # 提取列表页代理配置 (列表页采集应仅使用站点任务自身配置的代理，不从规则继承)
        list_proxy_pool_group = scraper_doc.get("proxy_pool_group") or params_config.get("proxy_pool_group")
        list_proxy = scraper_doc.get("proxy") or params_config.get("proxy")
        
        # 统一处理空字符串和空对象
        if not list_proxy_pool_group:
            list_proxy_pool_group = None
        if list_proxy and not list_proxy.get("server"):
            list_proxy = None
            
        # 2. 详情页代理逻辑：如果 scraper 本身没设代理，尝试从关联规则中继承
        # 注意：这里我们单独定义 detail_proxy，确保与 list_proxy 隔离
        detail_proxy_pool_group = list_proxy_pool_group
        detail_proxy = list_proxy
        
        if not detail_proxy_pool_group and not detail_proxy:
            if rule_doc:
                detail_proxy_pool_group = rule_doc.get("proxy_pool_group")
                detail_proxy = rule_doc.get("proxy")
                
                # 处理从规则中继承的可能为空的值
                if not detail_proxy_pool_group:
                    detail_proxy_pool_group = None
                if detail_proxy and not detail_proxy.get("server"):
                    detail_proxy = None
                
                if detail_proxy_pool_group or detail_proxy:
                    logger.info(f"Detail tasks will inherit proxy from rule {rule_doc.get('domain')}: group={detail_proxy_pool_group}")
        
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
                "proxy": list_proxy,
                "proxy_pool_group": list_proxy_pool_group,
                "cookies": get_val("cookies"),
                "intercept_apis": get_val("intercept_apis"),
                "intercept_continue": get_val("intercept_continue", False),
                "max_pages": scraper_doc.get("max_pages", 1),
                "max_retries": scraper_doc.get("max_retries", 0),
                "pagination_next_xpath": scraper_doc.get("pagination_next_xpath")
            }
        )
        
        # 提取抓取到的列表项和分页信息
        items = result.get("items", [])
        pages = result.get("pages", [])
        
        # 2.1 持久化站点采集执行记录 (按页存储：HTML、截图、性能数据等)
        try:
            # 如果有分页信息，按页存储；否则存储单条汇总记录
            if pages:
                execution_docs = []
                for p in pages:
                    execution_docs.append({
                        "scraper_id": ObjectId(scraper_id),
                        "scraper_name": scraper_name,
                        "url": p.get("url", scraper_doc["url"]),
                        "page_num": p.get("page_num", 1),
                        "status": result.get("status", "success"),
                        "error": result.get("error"),
                        "html": p.get("html") if get_val("save_html", True) else None,
                        "screenshot": p.get("screenshot"),
                        "items_count": p.get("count", 0),
                        "items": p.get("items", []), 
                        "duration": result.get("duration", 0) / len(pages), # 估算单页耗时
                        "engine": get_val("engine", "playwright"),
                        "created_at": datetime.now()
                    })
                if execution_docs:
                    mongo.db.scraper_executions.insert_many(execution_docs)
                    logger.info(f"Stored {len(execution_docs)} scraper execution records for {scraper_name}")
            else:
                # 兜底：存储单条汇总记录
                execution_doc = {
                    "scraper_id": ObjectId(scraper_id),
                    "scraper_name": scraper_name,
                    "url": scraper_doc["url"],
                    "status": result.get("status", "success"),
                    "error": result.get("error"),
                    "html": result.get("html") if get_val("save_html", True) else None,
                    "screenshot": result.get("screenshot"),
                    "items_count": len(items),
                    "items": items, 
                    "duration": result.get("duration", 0),
                    "engine": get_val("engine", "playwright"),
                    "created_at": datetime.now()
                }
                mongo.db.scraper_executions.insert_one(execution_doc)
                logger.info(f"Stored single scraper execution record for {scraper_name}")
        except Exception as e:
            logger.error(f"Failed to store scraper execution record: {e}")
        
        if result.get("status") == "failed":
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Scraper task failed: {error_msg}")
            await update_scraper_status(scraper_id, "failed", error_msg)
            return
            
        # 3. 为每个提取到的链接创建详情采集任务 (仅在成功且有项目时)
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
                proxy=detail_proxy,
                proxy_pool_group=detail_proxy_pool_group,
                cookies=get_val("cookies"),
                intercept_apis=get_val("intercept_apis"),
                intercept_continue=get_val("intercept_continue", False),
                storage_type=get_val("storage_type", "mongo"),
                mongo_collection=get_val("mongo_collection"),
                oss_path=get_val("oss_path"),
                save_html=get_val("save_html", True),
                return_cookies=get_val("return_cookies", False),
                screenshot=get_val("screenshot", False),
                is_fullscreen=get_val("is_fullscreen", False),
                max_retries=get_val("max_retries", 0)
            )

            if rule_doc:
                params.parser = rule_doc.get("parser_type")
                params.parser_config = rule_doc.get("parser_config")
                params.matched_rule = rule_doc.get("domain")
                
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
        # 更新状态为成功
        await update_scraper_status(scraper_id, "success")
        
    except Exception as e:
        logger.error(f"Error executing scraper task: {e}", exc_info=True)
        await update_scraper_status(scraper_id, "failed", str(e))

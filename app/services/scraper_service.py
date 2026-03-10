import json
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

async def create_detail_tasks(scraper_doc: dict, items: list, execution_type: str = "production"):
    """
    为提取到的列表项创建详情抓取任务
    
    Args:
        scraper_doc: 站点配置文档
        items: 提取到的列表项
        execution_type: 执行类型 (production 或 test)
    """
    scraper_id = str(scraper_doc["_id"])
    scraper_name = scraper_doc["name"]
    params_config = scraper_doc.get("params", {})
    
    # 0. 获取规则信息
    rule_id = scraper_doc.get("rule_id")
    rule_doc = None
    if rule_id:
        try:
            query = {"_id": ObjectId(rule_id)} if ObjectId.is_valid(rule_id) else {"id": rule_id}
            rule_doc = mongo.db.parsing_rules.find_one(query)
        except Exception as e:
            logger.warning(f"Failed to fetch rule {rule_id}: {e}")

    # 1. 代理逻辑
    list_proxy_pool_group = scraper_doc.get("proxy_pool_group") or params_config.get("proxy_pool_group")
    list_proxy = scraper_doc.get("proxy") or params_config.get("proxy")
    
    detail_proxy_pool_group = list_proxy_pool_group
    detail_proxy = list_proxy
    
    if not detail_proxy_pool_group and not detail_proxy and rule_doc:
        detail_proxy_pool_group = rule_doc.get("proxy_pool_group")
        detail_proxy = rule_doc.get("proxy")

    def get_val(key, default=None):
        return params_config.get(key, scraper_doc.get(key, default))

    count = 0
    for item in items:
        link = item.get("link")
        if not link: continue
            
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
            if rule_doc.get("parser_type") == "xpath":
                params.parser_config = {"rules": rule_doc.get("parser_config", {}).get("rules", {})}
            elif rule_doc.get("parser_type") == "llm":
                params.parser_config = {"fields": rule_doc.get("llm_fields", [])}
            else:
                params.parser_config = rule_doc.get("parser_config")
                
            params.matched_rule = rule_doc.get("domain")
            
            # 继承配置
            if not params.cookies and rule_doc.get("cookies"):
                try:
                    rule_cookies = rule_doc.get("cookies")
                    if isinstance(rule_cookies, str) and (rule_cookies.strip().startswith('{') or rule_cookies.strip().startswith('[')):
                        params.cookies = json.loads(rule_cookies)
                    else:
                        params.cookies = rule_cookies
                except: params.cookies = rule_cookies

            if not params.user_agent and rule_doc.get("user_agent"):
                params.user_agent = rule_doc.get("user_agent")
            if rule_doc.get("viewport"):
                params.viewport = rule_doc.get("viewport")
            if rule_doc.get("wait_for"): params.wait_for = rule_doc.get("wait_for")
            if rule_doc.get("wait_time"): params.wait_time = rule_doc.get("wait_time")
            if rule_doc.get("timeout"): params.timeout = rule_doc.get("timeout")
            if rule_doc.get("wait_for_selector"): params.selector = rule_doc.get("wait_for_selector")
            if "stealth" in rule_doc: params.stealth = rule_doc.get("stealth")
            if "no_images" in rule_doc: params.block_images = rule_doc.get("no_images")
            if rule_doc.get("engine"): params.engine = rule_doc.get("engine")
            
            if rule_doc.get("parser_type") == "gne":
                params.engine = "playwright"

        request = ScrapeRequest(
            url=link,
            params=params,
            execution_type=execution_type
        )
        request.schedule_id = f"scraper_{scraper_id}"
        await task_service.create_task(request)
        count += 1
    
    return count

async def execute_scraper_task(scraper_doc: dict, execution_type: str = "production"):
    """后台执行站点采集任务"""
    scraper_id = str(scraper_doc["_id"])
    scraper_name = scraper_doc["name"]
    
    try:
        # 检查站点是否启用
        if not scraper_doc.get("enabled", True):
            logger.info(f"Scraper task skipped (disabled): {scraper_name} ({scraper_id})")
            return
            
        logger.info(f"Starting scraper task ({execution_type}): {scraper_name} ({scraper_id})")
        
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
        # if not rule_doc:
        #     rule_doc = _match_rule_by_url(scraper_doc["url"])
        #     if rule_doc:
        #         logger.info(f"Automatically matched rule {rule_doc.get('domain')} for detail tasks of scraper {scraper_name}")
        
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
                        "created_at": datetime.now(),
                        "execution_type": execution_type
                    })
                if execution_docs:
                    mongo.scraper_executions.insert_many(execution_docs)
                    logger.info(f"Stored {len(execution_docs)} scraper execution records for {scraper_name}")
            else:
                # 兜底：存储单条汇总记录
                execution_doc = {
                    "scraper_id": ObjectId(scraper_id),
                    "scraper_name": scraper_name,
                    "url": scraper_doc["url"],
                    "page_num": 1,
                    "status": result.get("status", "success"),
                    "error": result.get("error"),
                    "html": result.get("html") if get_val("save_html", True) else None,
                    "screenshot": result.get("screenshot"),
                    "items_count": len(items),
                    "items": items,
                    "duration": result.get("duration", 0),
                    "engine": get_val("engine", "playwright"),
                    "created_at": datetime.now(),
                    "execution_type": execution_type
                }
                mongo.scraper_executions.insert_one(execution_doc)
                logger.info(f"Stored single scraper execution record for {scraper_name}")
        except Exception as e:
            logger.error(f"Failed to store scraper execution record: {e}")
        
        if result.get("status") == "failed":
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Scraper task failed: {error_msg}")
            await update_scraper_status(scraper_id, "failed", error_msg)
            return
            
        # 3. 为每个提取到的链接创建详情采集任务 (仅在成功且有项目时)
        count = await create_detail_tasks(scraper_doc, items, execution_type=execution_type)
        
        logger.info(f"Created {count} detail scraping tasks for scraper: {scraper_name}")
        # 更新状态为成功
        await update_scraper_status(scraper_id, "success")
        
    except Exception as e:
        logger.error(f"Error executing scraper task: {e}", exc_info=True)
        await update_scraper_status(scraper_id, "failed", str(e))

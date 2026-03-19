import asyncio
import logging
import re
import time
import os
import base64
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from playwright.async_api import Page, BrowserContext, Frame
from app.core.browser import browser_manager
from app.core.config import settings
from app.models.workflow import WorkflowBase, WorkflowNode, NodeType, WorkflowEdge

logger = logging.getLogger(__name__)

from app.db.mongo import mongo
from bson import ObjectId

class WorkflowExecutor:
    """工作流执行引擎"""

    def __init__(self, workflow: WorkflowBase, workflow_id: str, mode: str = "prod", execution_id: Optional[str] = None):
        self.workflow = workflow
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.mode = mode
        self.variables: Dict[str, Any] = workflow.variables.copy()
        self.logs: List[Dict[str, Any]] = []
        self.screenshots: List[str] = []
        self.context: Optional[BrowserContext] = None
        self.current_page: Optional[Page] = None
        self.current_frame: Optional[Union[Page, Frame]] = None
        self.is_running = False
        self.engine = "playwright" # 默认引擎
        
        self._node_map: Dict[str, WorkflowNode] = {node.id: node for node in workflow.nodes}
        self._edge_map: Dict[str, List[WorkflowEdge]] = {}
        for edge in workflow.edges:
            if edge.source not in self._edge_map:
                self._edge_map[edge.source] = []
            self._edge_map[edge.source].append(edge)
        
        # 进度追踪
        self.total_nodes = len(workflow.nodes)
        self.completed_nodes = 0

    def _get_node_param(self, node: WorkflowNode, key: str, default: Any = None) -> Any:
        """安全地获取节点参数，处理 None 值"""
        val = node.params.get(key)
        return val if val is not None else default

    def _update_progress(self, status: str = "running"):
        """更新执行进度到数据库"""
        if not self.execution_id:
            return
            
        mongo.db.workflow_executions.update_one(
            {"_id": ObjectId(self.execution_id)},
            {"$set": {
                "status": status,
                "completed_nodes": self.completed_nodes,
                "total_nodes": self.total_nodes,
                "updated_at": datetime.now()
            }}
        )

    def _log(self, level: str, message: str, node_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        log_entry = {
            "workflow_id": ObjectId(self.workflow_id),
            "mode": self.mode,
            "timestamp": datetime.now(),
            "level": level,
            "message": message,
            "node_id": node_id,
            "data": data
        }
        self.logs.append(log_entry)
        mongo.db.workflow_logs.insert_one(log_entry)
        logger.info(f"[Workflow {self.workflow.name}] {message}")

    def _resolve_variables(self, text: Any) -> Any:
        """解析字符串中的变量 {{var_name}}"""
        if not isinstance(text, str):
            return text
        
        def replace_match(match):
            var_name = match.group(1).strip()
            return str(self.variables.get(var_name, match.group(0)))

        return re.sub(r"\{\{(.*?)\}\}", replace_match, text)

    def _get_selector(self, node: WorkflowNode) -> Optional[str]:
        """获取并解析选择器，支持多种模式 (css, xpath)"""
        selector = node.params.get("selector")
        if not selector:
            return None
        
        resolved_selector = self._resolve_variables(selector)
        selector_type = node.params.get("selector_type", "css")
        
        if selector_type == "xpath" and not resolved_selector.startswith("xpath="):
            return f"xpath={resolved_selector}"
        elif selector_type == "css" and not resolved_selector.startswith("css="):
            # Playwright 默认就是 CSS，但显式加上前缀更清晰
            return f"css={resolved_selector}"
        
        return resolved_selector

    async def run(self):
        """执行工作流"""
        self.is_running = True
        self._log("INFO", f"Starting workflow execution: {self.workflow.name} (Mode: {self.mode})")
        logger.info(f"DEBUG: Execution ID: {self.execution_id}")
        
        try:
            logger.info("DEBUG: Getting browser...")
            browser = await browser_manager.get_browser()
            logger.info("DEBUG: Browser obtained. Creating context...")
            
            # 设置默认视口大小
            viewport = {
                "width": settings.default_viewport_width,
                "height": settings.default_viewport_height
            }
            
            self.context = await browser.new_context(viewport=viewport)
            self.current_page = await self.context.new_page()
            self.current_frame = self.current_page

            # 找到开始节点并提取引擎配置
            start_node = next((n for n in self.workflow.nodes if n.type == NodeType.START), None)
            if not start_node:
                raise ValueError("No start node found in workflow")
            
            self.engine = self._get_node_param(start_node, "engine", "playwright")
            logger.info(f"DEBUG: Using engine: {self.engine}")

            logger.info(f"DEBUG: Starting execution from node {start_node.id}")
            await self._execute_node(start_node.id)
            self._log("INFO", "Workflow execution completed successfully", data={"final_variables": self.variables})
            
            # 保存最终结果到对应集合
            collection = mongo.db.workflow_results if self.mode == "prod" else mongo.db.workflow_test_results
            result_data = {
                "workflow_id": ObjectId(self.workflow_id),
                "timestamp": datetime.now(),
                "status": "success",
                "variables": self.variables,
                "screenshots": self.screenshots
            }
            logger.info(f"DEBUG: Saving success result to {collection.name}")
            collection.insert_one(result_data)
            
            # 更新进度为完成（确保在保存结果之后）
            self.completed_nodes = self.total_nodes
            self._update_progress("completed")
        except Exception as e:
            logger.error(f"DEBUG: Execution error: {str(e)}", exc_info=True)
            self._log("ERROR", f"Workflow execution failed: {str(e)}", data={"variables_at_error": self.variables})
            
            # 保存错误结果
            collection = mongo.db.workflow_results if self.mode == "prod" else mongo.db.workflow_test_results
            result_data = {
                "workflow_id": ObjectId(self.workflow_id),
                "timestamp": datetime.now(),
                "status": "failed",
                "error": str(e),
                "variables": self.variables,
                "screenshots": self.screenshots
            }
            logger.info(f"DEBUG: Saving failed result to {collection.name}")
            collection.insert_one(result_data)
            
            # 更新进度为失败（在保存结果之后）
            self._update_progress("failed")
            raise
        finally:
            self.is_running = False
            if self.context:
                await self.context.close()

    async def _execute_node(self, node_id: str):
        """递归/循环执行节点"""
        if not self.is_running:
            return

        node = self._node_map.get(node_id)
        if not node:
            return

        self._log("INFO", f"Executing node: {node.label} ({node.type})", node_id)
        
        # 更新进度
        self.completed_nodes += 1
        self._update_progress("running")
        
        next_node_id = None
        try:
            if node.type == NodeType.GOTO:
                url = self._resolve_variables(self._get_node_param(node, "url"))
                wait_until = self._get_node_param(node, "wait_until", "networkidle")
                timeout = self._get_node_param(node, "timeout", 30000)
                await self.current_frame.goto(url, wait_until=wait_until, timeout=timeout)
            
            elif node.type == NodeType.CLICK:
                selector = self._get_selector(node)
                timeout = self._get_node_param(node, "timeout", 30000)
                click_count = self._get_node_param(node, "click_count", 1)
                delay = self._get_node_param(node, "delay", 0)
                await self.current_frame.click(
                    selector, 
                    timeout=timeout, 
                    click_count=click_count,
                    delay=delay
                )
            
            elif node.type == NodeType.TYPE:
                selector = self._get_selector(node)
                value = self._resolve_variables(self._get_node_param(node, "value", ""))
                delay = self._get_node_param(node, "delay", 0)
                # Playwright's fill doesn't support delay, use type instead if delay > 0
                if delay > 0:
                    await self.current_frame.click(selector)
                    await self.current_frame.type(selector, value, delay=delay)
                else:
                    await self.current_frame.fill(selector, value)
            
            elif node.type == NodeType.WAIT:
                selector = self._get_selector(node)
                timeout = self._get_node_param(node, "timeout", 5000)
                if selector:
                    await self.current_frame.wait_for_selector(selector, timeout=timeout)
                else:
                    await asyncio.sleep(timeout / 1000)
            
            elif node.type == NodeType.EXTRACT:
                selector = self._get_selector(node)
                var_name = self._get_node_param(node, "variable_name")
                attr = self._get_node_param(node, "attribute")
                
                if attr:
                    value = await self.current_frame.get_attribute(selector, attr)
                else:
                    value = await self.current_frame.inner_text(selector)
                
                if var_name:
                    self.variables[var_name] = value
                    self._log("INFO", f"Extracted value to variable '{var_name}': {value}", node_id)

            elif node.type == NodeType.GET_INFO:
                info_type = self._get_node_param(node, "info_type", "url")
                var_name = self._get_node_param(node, "variable_name")
                
                value = None
                if info_type == "url":
                    value = self.current_page.url
                elif info_type == "title":
                    value = await self.current_page.title()
                elif info_type == "cookies":
                    value = await self.context.cookies()
                elif info_type == "content":
                    value = await self.current_page.content()
                
                if var_name:
                    self.variables[var_name] = value
                    self._log("INFO", f"Extracted {info_type} to variable '{var_name}': {value if info_type != 'content' else '(HTML content)'}", node_id)
                else:
                    self._log("WARNING", f"GET_INFO executed but no variable name provided to save {info_type}", node_id)
            
            elif node.type == NodeType.IF:
                # 简单条件判断：检查元素是否存在
                selector = self._get_selector(node)
                exists = await self.current_frame.query_selector(selector) is not None
                
                # 找到匹配条件的边
                edges = self._edge_map.get(node_id, [])
                if exists:
                    # True 分支 (假设 condition_index 0 为 True)
                    edge = next((e for e in edges if e.condition_index == 0), None)
                else:
                    # False 分支 (假设 condition_index 1 为 False)
                    edge = next((e for e in edges if e.condition_index == 1), None)
                
                if edge:
                    next_node_id = edge.target
            
            elif node.type == NodeType.TAB_SWITCH:
                index = int(self._get_node_param(node, "index", 0))
                pages = self.context.pages
                if index < len(pages):
                    self.current_page = pages[index]
                    self.current_frame = self.current_page
                    await self.current_page.bring_to_front()
            
            elif node.type == NodeType.IFRAME_SWITCH:
                selector = self._get_selector(node)
                if selector == "main" or selector == "css=main":
                    self.current_frame = self.current_page
                else:
                    self.current_frame = self.current_page.frame_locator(selector)

            elif node.type == NodeType.SCREENSHOT:
                base_name = self._resolve_variables(self._get_node_param(node, "name", "screenshot"))
                full_page = self._get_node_param(node, "full_page", False) # 默认不截取全屏，除非明确配置
                logger.info(f"Taking screenshot: {base_name} (Base64, full_page={full_page})")
                try:
                    # 确保页面处于稳定状态
                    await self.current_page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass

                try:
                    # 获取截图字节数据并转换为 base64 字符串
                    # 使用 jpeg 格式并压缩质量以减小 Base64 字符串长度，确保能存入 MongoDB
                    screenshot_bytes = await self.current_page.screenshot(
                        type="jpeg", 
                        quality=80,
                        full_page=full_page
                    )
                    base64_data = base64.b64encode(screenshot_bytes).decode("utf-8")
                    data_uri = f"data:image/jpeg;base64,{base64_data}"
                    
                    self.screenshots.append(data_uri)
                    self._log("INFO", f"Screenshot captured (Base64): {base_name}", node_id, data={"screenshot_url": data_uri})
                    logger.info(f"DEBUG: Base64 screenshot captured (JPEG). Total now: {len(self.screenshots)}")
                except Exception as screenshot_error:
                    logger.error(f"Failed to take screenshot: {str(screenshot_error)}")
                    self._log("ERROR", f"Failed to take screenshot: {str(screenshot_error)}", node_id)

            elif node.type == NodeType.HOVER:
                selector = self._get_selector(node)
                timeout = self._get_node_param(node, "timeout", 30000)
                await self.current_frame.hover(selector, timeout=timeout)

            elif node.type == NodeType.KEYPRESS:
                key = self._get_node_param(node, "key")
                delay = self._get_node_param(node, "delay", 0)
                await self.current_frame.press(key, delay=delay)

            # 默认下一节点处理 (非分支节点)
            if not next_node_id and node.type != NodeType.IF:
                edges = self._edge_map.get(node_id, [])
                if edges:
                    next_node_id = edges[0].target

            if next_node_id:
                await self._execute_node(next_node_id)

        except Exception as e:
            self._log("ERROR", f"Error in node {node.label}: {str(e)}", node_id)
            # 异常处理逻辑
            error_edge = next((e for e in self._edge_map.get(node_id, []) if e.label == "error"), None)
            if error_edge:
                await self._execute_node(error_edge.target)
            else:
                raise

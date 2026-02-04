from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.models.rule import ParsingRule, ParsingRuleCreate, ParsingRuleUpdate
from app.db.mongo import mongo
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/rules", tags=["解析规则"])

def format_rule(rule_data: dict) -> dict:
    """格式化 MongoDB 文档为 API 响应模型"""
    if not rule_data:
        return None
    rule_data["id"] = str(rule_data.pop("_id"))
    return rule_data

@router.get("/", response_model=List[ParsingRule])
async def get_rules(current_user: dict = Depends(get_current_user)):
    """获取所有解析规则"""
    rules = list(mongo.parsing_rules.find().sort("updated_at", -1))
    return [format_rule(r) for r in rules]

@router.get("/domain/{domain}", response_model=List[ParsingRule])
async def get_rules_by_domain(domain: str, current_user: dict = Depends(get_current_user)):
    """根据域名获取解析规则列表"""
    rules = list(mongo.parsing_rules.find({"domain": domain}))
    return [format_rule(r) for r in rules]

@router.post("/", response_model=ParsingRule)
async def create_rule(rule: ParsingRuleCreate, current_user: dict = Depends(get_current_user)):
    """创建或更新解析规则（按域名唯一）"""
    try:
        rule_data = rule.model_dump()
        rule_data["updated_at"] = datetime.now()
        
        # 检查是否已存在相同域名的规则
        existing = mongo.parsing_rules.find_one({
            "domain": rule.domain
        })
        
        if existing:
            # 如果已存在，则更新
            mongo.parsing_rules.update_one(
                {"_id": existing["_id"]},
                {"$set": rule_data}
            )
            rule_data["_id"] = existing["_id"]
            rule_data["created_at"] = existing.get("created_at", datetime.now())
        else:
            # 如果不存在，则插入
            rule_data["created_at"] = datetime.now()
            result = mongo.parsing_rules.insert_one(rule_data)
            rule_data["_id"] = result.inserted_id
            
        return format_rule(rule_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{rule_id}", response_model=ParsingRule)
async def update_rule(rule_id: str, rule_update: ParsingRuleUpdate, current_user: dict = Depends(get_current_user)):
    """更新解析规则"""
    try:
        update_data = {k: v for k, v in rule_update.model_dump().items() if v is not None}
        update_data["updated_at"] = datetime.now()
        
        result = mongo.parsing_rules.update_one(
            {"_id": ObjectId(rule_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        updated_rule = mongo.parsing_rules.find_one({"_id": ObjectId(rule_id)})
        return format_rule(updated_rule)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    """删除解析规则"""
    try:
        result = mongo.parsing_rules.delete_one({"_id": ObjectId(rule_id)})
        if result.deleted_count > 0:
            return {"message": "Rule deleted"}
        raise HTTPException(status_code=404, detail="Rule not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

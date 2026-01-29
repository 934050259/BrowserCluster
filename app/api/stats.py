"""
统计数据 API 路由模块

提供任务统计、队列状态等接口
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from app.models.task import StatsResponse
from app.db.mongo import mongo
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/stats", tags=["Stats"])


@router.get("/", response_model=StatsResponse)
async def get_stats(current_user: dict = Depends(get_current_user)):
    """
    获取统计信息

    Returns:
        StatsResponse: 包含今日统计、历史统计和队列状态的响应
    """
    # 计算今日时间范围
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    tomorrow_start = today_start + timedelta(days=1)

    # 1. 获取今日统计
    pipeline_today = [
        {
            "$match": {
                "created_at": {"$gte": today_start, "$lt": tomorrow_start}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "success": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
                "total_duration": {"$sum": {"$ifNull": ["$result.metadata.load_time", 0]}},
                "completed_count": {"$sum": {"$cond": [{"$in": ["$status", ["success", "failed"]]}, 1, 0]}}
            }
        }
    ]
    today_data = list(mongo.tasks.aggregate(pipeline_today))
    
    # 2. 获取昨日统计（用于计算趋势）
    pipeline_yesterday = [
        {
            "$match": {
                "created_at": {"$gte": yesterday_start, "$lt": today_start}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "success": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
                "total_duration": {"$sum": {"$ifNull": ["$result.metadata.load_time", 0]}},
                "completed_count": {"$sum": {"$cond": [{"$in": ["$status", ["success", "failed"]]}, 1, 0]}}
            }
        }
    ]
    yesterday_data = list(mongo.tasks.aggregate(pipeline_yesterday))

    def process_stats(data_list):
        if not data_list:
            return {"total": 0, "success": 0, "failed": 0, "avg_duration": 0}
        stats = data_list[0]
        avg_duration = (
            stats["total_duration"] / stats["completed_count"]
            if stats["completed_count"] > 0 else 0
        )
        return {
            "total": stats["total"],
            "success": stats["success"],
            "failed": stats["failed"],
            "avg_duration": round(avg_duration, 2)
        }

    today_stats = process_stats(today_data)
    yesterday_stats = process_stats(yesterday_data)

    # 计算趋势百分比
    def calculate_trend(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    trends = {
        "total": calculate_trend(today_stats["total"], yesterday_stats["total"]),
        "success": calculate_trend(today_stats["success"], yesterday_stats["success"]),
        "failed": calculate_trend(today_stats["failed"], yesterday_stats["failed"]),
        "avg_duration": calculate_trend(today_stats["avg_duration"], yesterday_stats["avg_duration"])
    }

    # 3. 统计各状态任务数量 (实时队列)
    queue_stats = {
        "pending": mongo.tasks.count_documents({"status": "pending"}),
        "processing": mongo.tasks.count_documents({"status": "processing"}),
        "success": mongo.tasks.count_documents({"status": "success"}),
        "failed": mongo.tasks.count_documents({"status": "failed"})
    }

    # 4. 获取历史统计 (最近 7 天，用于图表)
    history_pipeline = [
        {
            "$match": {
                "created_at": {"$gte": now - timedelta(days=7)}
            }
        },
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "total": {"$sum": 1},
                "success": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    history_data = list(mongo.tasks.aggregate(history_pipeline))

    return StatsResponse(
        today=today_stats,
        yesterday=yesterday_stats,
        trends=trends,
        queue=queue_stats,
        history=history_data
    )

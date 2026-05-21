"""History API endpoints"""

import asyncio
from fastapi import APIRouter
from ..database import get_recent_alerts

router = APIRouter()


@router.get("/history")
async def get_history():
    """Get alert history"""
    try:
        return await asyncio.to_thread(get_recent_alerts, 100)
    except Exception as e:
        return {"error": str(e)}

from fastapi import APIRouter, Depends
from typing import Dict

from app.db.database import test_db_connection
from app.db.redis_client import redis_client

router = APIRouter()

@router.get("")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify database and redis connectivity.
    """
    db_ok = await test_db_connection()
    
    redis_ok = False
    try:
        redis_ok = await redis_client.ping()
    except Exception:
        pass
        
    return {
        "status": "ok" if db_ok and redis_ok else "error",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected"
    }

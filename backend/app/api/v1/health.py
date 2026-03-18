from fastapi import APIRouter, Depends
from typing import Dict

from app.db.database import test_db_connection
from app.db import redis_client as rc

router = APIRouter()

@router.get("")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify database and redis connectivity.
    """
    db_ok = await test_db_connection()
    
    redis_ok = False
    try:
        print(f"DEBUG HEALTH: rc.redis_client is {rc.redis_client}")
        if rc.redis_client:
            redis_ok = await rc.redis_client.ping()
            print(f"DEBUG HEALTH: ping result is {redis_ok}")
        else:
            print("DEBUG HEALTH: rc.redis_client is NONE")
    except Exception as e:
        print(f"DEBUG HEALTH: ping error {type(e).__name__}: {e}")
        pass
        
    return {
        "status": "ok" if db_ok and redis_ok else "error",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected"
    }

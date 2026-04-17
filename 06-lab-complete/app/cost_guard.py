import time
import redis
from fastapi import HTTPException
from app.config import settings

r = redis.from_url(settings.redis_url) if settings.redis_url else None

def check_and_record_cost(input_tokens: int, output_tokens: int):
    if not r:
        return  # skip if no Redis

    today = time.strftime("%Y-%m-%d")
    key = f"cost:{today}"
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    
    current = float(r.get(key) or 0)
    if current >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=503,
            detail="Daily budget exhausted. Try tomorrow."
        )
    
    r.incrbyfloat(key, cost)
    r.expire(key, 86400 * 2)  # Keep for 2 days

def get_daily_cost() -> float:
    if not r:
        return 0.0
    today = time.strftime("%Y-%m-%d")
    key = f"cost:{today}"
    return float(r.get(key) or 0)

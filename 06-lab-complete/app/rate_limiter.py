import time
import redis
from fastapi import HTTPException
from app.config import settings

r = redis.from_url(settings.redis_url) if settings.redis_url else None

def check_rate_limit(key: str):
    if not r:
        return  # skip if no Redis

    now = time.time()
    window_key = f"rate:{key}"
    
    pipe = r.pipeline()
    pipe.zremrangebyscore(window_key, 0, now - 60)
    pipe.zadd(window_key, {str(now): now})
    pipe.zcard(window_key)
    pipe.expire(window_key, 120)
    results = pipe.execute()
    count = results[2]
    
    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )

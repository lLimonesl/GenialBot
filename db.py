# db.py
import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

async def get_pool():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=5
        )
    return _pool


async def close_pool():
    global _pool
    if _pool is None:
        return
    await _pool.close()
    _pool = None

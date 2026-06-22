import asyncio
import json
from db import get_pool
from load_world import WORLD_META, WORLD_RULES, SOCIAL_HIERARCHY

async def init_pg():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(open("schema.sql").read())

        await conn.execute("""
        INSERT INTO world (id, current_day, rules, hierarchy, meta)
        VALUES (1, 0, $1, $2, $3)
        ON CONFLICT (id) DO NOTHING
        """, WORLD_RULES, json.dumps(SOCIAL_HIERARCHY), json.dumps(WORLD_META))

    print("PostgreSQL inicializado")

asyncio.run(init_pg())

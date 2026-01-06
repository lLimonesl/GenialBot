import asyncio
import json
from db import get_pool
from world_data import WORLD_RULES, SOCIAL_HIERARCHY

async def init_pg():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(open("schema.sql").read())

        await conn.execute("""
        INSERT INTO world (id, current_day, rules, hierarchy)
        VALUES (1, 0, $1, $2)
        ON CONFLICT (id) DO NOTHING
        """, WORLD_RULES, json.dumps(SOCIAL_HIERARCHY))

    print("PostgreSQL inicializado")

asyncio.run(init_pg())

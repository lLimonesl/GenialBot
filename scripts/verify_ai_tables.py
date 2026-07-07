import asyncio
import os

import asyncpg


AI_TABLES = (
    "ai_runs",
    "entity_relationships",
    "memory_chunks",
    "prompt_snapshots",
    "story_facts",
)


async def main():
    database_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_PUBLIC_URL or DATABASE_URL is required")

    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=1)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY($1::text[])
            ORDER BY table_name
            """,
            list(AI_TABLES),
        )
    await pool.close()

    found = [row["table_name"] for row in rows]
    print(found)


if __name__ == "__main__":
    asyncio.run(main())

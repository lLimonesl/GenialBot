# database.py
import json
from db import get_pool

# ---------- INIT DB (solo PostgreSQL) ----------

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            race TEXT NOT NULL,
            social_status TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Vivo',
            level INTEGER NOT NULL DEFAULT 1,
            weapon TEXT,
            amulet TEXT,
            pet JSONB,
            abilities JSONB,
            passives JSONB,
            final_move JSONB,
            current_kingdom TEXT,
            notes TEXT
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS world (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_day INTEGER NOT NULL,
            rules TEXT NOT NULL,
            hierarchy JSONB NOT NULL,
            meta JSONB
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id SERIAL PRIMARY KEY,
            day INTEGER UNIQUE NOT NULL,
            title TEXT,
            full_text TEXT,
            summary TEXT
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS character_arcs (
            id SERIAL PRIMARY KEY,
            character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
            arc_name TEXT,
            arc_goal TEXT,
            arc_status TEXT,
            arc_progress INTEGER
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            day INTEGER,
            question TEXT,
            options JSONB,
            result TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS pov_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_character_id INTEGER REFERENCES characters(id)
        );
        """)

                # Inicializar world
        await conn.execute("""
            INSERT INTO world (id, current_day, rules, hierarchy)
            VALUES (1, 0, '', '{}'::jsonb)
            ON CONFLICT (id) DO NOTHING
        """)

        # Inicializar POV
        await conn.execute("""
            INSERT INTO pov_state (id, current_character_id)
            VALUES (1, NULL)
            ON CONFLICT (id) DO NOTHING
        """)

# ---------- WORLD ----------

async def get_world_state():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT current_day, rules FROM world WHERE id = 1"
        )
        return row["current_day"], row["rules"]

async def increment_day():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE world SET current_day = current_day + 1 WHERE id = 1"
        )

# ---------- CHARACTERS ----------

async def get_characters():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, race, status
            FROM characters
            WHERE status != 'Muerto'
        """)
        return rows
    
async def get_full_characters():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT
                name,
                race,
                status,
                weapon,
                amulet,
                pet,
                abilities,
                passives,
                final_move
            FROM characters
            WHERE status != 'Muerto'
        """)

async def apply_level_ups(level_ups):
    """
    level_ups = [(name, amount), ...]
    """
    if not level_ups:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for name, amount in level_ups:
            await conn.execute("""
                UPDATE characters
                SET level = level + $1
                WHERE name = $2
            """, amount, name)


async def get_character_by_name(name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM characters WHERE name = $1",
            name
        )

async def set_character_status(name, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE characters SET status = $1 WHERE name = $2",
            status, name
        )

# ---------- DAILY LOGS ----------

async def save_day(title, full_text, summary):
    pool = await get_pool()
    async with pool.acquire() as conn:
        day = await conn.fetchval(
            "SELECT current_day FROM world WHERE id = 1"
        )

        new_day = day + 1

        await conn.execute("""
            INSERT INTO daily_logs (day, title, full_text, summary)
            VALUES ($1, $2, $3, $4)
        """, new_day, title, full_text, summary)

        await conn.execute(
            "UPDATE world SET current_day = $1 WHERE id = 1",
            new_day
        )

    return new_day


# ---------- ARCS ----------

async def get_active_arcs():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.name, a.arc_name, a.arc_goal, a.arc_progress
            FROM character_arcs a
            JOIN characters c ON c.id = a.character_id
            WHERE a.arc_status = 'active'
        """)
        return rows

# ---------- POV ----------

async def get_current_pov():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT c.name
            FROM pov_state p
            JOIN characters c ON c.id = p.current_character_id
            WHERE p.id = 1
        """)
        return row["name"] if row else None
    
# ---------- SET POV ----------

async def set_pov(name: str | None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if name is None:
            await conn.execute(
                "UPDATE pov_state SET current_character_id = NULL WHERE id = 1"
            )
            return

        row = await conn.fetchrow(
            "SELECT id FROM characters WHERE name = $1",
            name
        )

        if not row:
            return False

        await conn.execute("""
            INSERT INTO pov_state (id, current_character_id)
            VALUES (1, $1)
            ON CONFLICT (id)
            DO UPDATE SET current_character_id = $1
        """, row["id"])

    return True


# ---------- VOTES ----------

async def create_vote(day, question, options, source="ai"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO votes (day, question, options, status, source)
            VALUES ($1, $2, $3::jsonb, 'open', $4)
        """,
        day,
        question,
        json.dumps(options),
        source
        )

async def get_current_day():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT current_day FROM world WHERE id = 1"
        )

async def get_closed_votes(limit=3):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT question, result
            FROM votes
            WHERE status = 'closed'
            ORDER BY id DESC
            LIMIT $1
        """, limit)
        return rows

# ---------- MUERTE PERMANENTE ----------

async def kill_character(name: str, cause: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Obtener id del personaje
        row = await conn.fetchrow(
            "SELECT id FROM characters WHERE name = $1",
            name
        )

        if not row:
            return False  # personaje no existe

        character_id = row["id"]

        # Marcar como muerto
        await conn.execute(
            "UPDATE characters SET status = 'Muerto' WHERE id = $1",
            character_id
        )

        # Cerrar arcos activos
        await conn.execute(
            "UPDATE character_arcs SET arc_status = 'closed' WHERE character_id = $1",
            character_id
        )

        # Registrar evento en el día actual
        day = await conn.fetchval(
            "SELECT current_day FROM world WHERE id = 1"
        )

        await conn.execute("""
            INSERT INTO daily_logs (day, title, full_text, summary)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (day) DO NOTHING
        """,
            day,
            "Muerte de un Campeón",
            f"{name} ha muerto definitivamente. Causa: {cause}",
            f"Muerte permanente de {name}"
        )

    return True

# ---------- CERRAR VOTACIÓN ----------

async def close_vote(vote_id: int, result: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE votes
            SET result = $1,
                status = 'closed'
            WHERE id = $2
        """, result, vote_id)

# ---------- VOTACIONES ABIERTAS ----------

async def get_open_votes_older_than(hours: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT id, question, options
            FROM votes
            WHERE status = 'open'
              AND created_at <= NOW() - ($1 * INTERVAL '1 hour')
        """, hours)

# ---------- RESET GLOBAL ----------

async def reset_world_progress():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM daily_logs")
        await conn.execute("DELETE FROM votes")
        await conn.execute("DELETE FROM character_arcs")

        await conn.execute("""
            UPDATE world
            SET current_day = 0
            WHERE id = 1
        """)

        await conn.execute("""
            UPDATE pov_state
            SET current_character_id = NULL
            WHERE id = 1
        """)

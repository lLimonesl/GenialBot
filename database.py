# database.py
import json
from db import get_pool
from load_world import WORLD_META, WORLD_RULES, SOCIAL_HIERARCHY

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
            summary TEXT,
            weather TEXT
        );
        """)

        await conn.execute("ALTER TABLE daily_logs ADD COLUMN IF NOT EXISTS weather TEXT")

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
            source TEXT,
            message_id BIGINT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        await conn.execute("ALTER TABLE votes ADD COLUMN IF NOT EXISTS source TEXT")
        await conn.execute("ALTER TABLE votes ADD COLUMN IF NOT EXISTS message_id BIGINT")
        await conn.execute("ALTER TABLE votes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id SERIAL PRIMARY KEY,
            day INTEGER,
            character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,
            character_name TEXT,
            quote TEXT NOT NULL
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
            item_name TEXT NOT NULL,
            item_type TEXT,
            item_description TEXT,
            quantity INTEGER NOT NULL DEFAULT 1,
            obtained_day INTEGER,
            equipped BOOLEAN NOT NULL DEFAULT FALSE,
            UNIQUE(character_id, item_name)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS reputation (
            id SERIAL PRIMARY KEY,
            character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
            kingdom TEXT NOT NULL,
            fame_level INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            UNIQUE(character_id, kingdom)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS npcs (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            race TEXT,
            description TEXT,
            role TEXT,
            kingdom TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            first_appearance_day INTEGER,
            last_appearance_day INTEGER,
            notes TEXT
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS battle_logs (
            id SERIAL PRIMARY KEY,
            day INTEGER,
            participants JSONB,
            enemies JSONB,
            outcome TEXT,
            summary TEXT
        );
        """)

        # Inicializar world
        await conn.execute("""
            INSERT INTO world (id, current_day, rules, hierarchy, meta)
            VALUES (1, 0, $1, $2::jsonb, $3::jsonb)
            ON CONFLICT (id) DO NOTHING
        """, WORLD_RULES, json.dumps(SOCIAL_HIERARCHY), json.dumps(WORLD_META))

        await conn.execute("""
            UPDATE world
            SET rules = $1,
                hierarchy = $2::jsonb,
                meta = COALESCE(meta, $3::jsonb)
            WHERE id = 1
              AND rules = ''
        """, WORLD_RULES, json.dumps(SOCIAL_HIERARCHY), json.dumps(WORLD_META))

# ---------- WORLD ----------

async def get_world_state():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT current_day, rules FROM world WHERE id = 1"
        )
        return row["current_day"], row["rules"]

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
                level,
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

async def save_day(title, full_text, summary, weather=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        day = await conn.fetchval(
            "SELECT current_day FROM world WHERE id = 1"
        )

        new_day = day + 1

        await conn.execute("""
            INSERT INTO daily_logs (day, title, full_text, summary, weather)
            VALUES ($1, $2, $3, $4, $5)
        """, new_day, title, full_text, summary, weather)

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

async def create_character_arc(character_name, arc_name, arc_goal):
    pool = await get_pool()
    async with pool.acquire() as conn:
        character_id = await conn.fetchval(
            "SELECT id FROM characters WHERE name = $1",
            character_name
        )
        if not character_id:
            return False

        existing = await conn.fetchval("""
            SELECT id
            FROM character_arcs
            WHERE character_id = $1
              AND arc_name = $2
              AND arc_status = 'active'
        """, character_id, arc_name)

        if existing:
            return False

        await conn.execute("""
            INSERT INTO character_arcs (character_id, arc_name, arc_goal, arc_status, arc_progress)
            VALUES ($1, $2, $3, 'active', 0)
        """, character_id, arc_name, arc_goal)
        return True

async def update_arc_progress(character_name, arc_name, amount):
    pool = await get_pool()
    async with pool.acquire() as conn:
        character_id = await conn.fetchval(
            "SELECT id FROM characters WHERE name = $1",
            character_name
        )
        if not character_id:
            return False

        await conn.execute("""
            UPDATE character_arcs
            SET arc_progress = LEAST(100, arc_progress + $1),
                arc_status = CASE WHEN arc_progress + $1 >= 100 THEN 'completed' ELSE arc_status END
            WHERE character_id = $2
              AND arc_name = $3
              AND arc_status = 'active'
        """, amount, character_id, arc_name)
        return True

# ---------- HISTORIAL / STATS ----------

async def get_day_log(day: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT day, title, full_text, summary, weather
            FROM daily_logs
            WHERE day = $1
        """, day)

async def search_logs_by_character(name: str, limit=5):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT day, title, summary, weather
            FROM daily_logs
            WHERE full_text ILIKE $1 OR summary ILIKE $1
            ORDER BY day DESC
            LIMIT $2
        """, f"%{name}%", limit)

async def get_character_stats(name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        character = await conn.fetchrow("""
            SELECT id, name, race, social_status, status, level, weapon, amulet,
                   pet, abilities, passives, final_move, current_kingdom, notes
            FROM characters
            WHERE name ILIKE $1
        """, name)
        if not character:
            return None

        arcs = await conn.fetch("""
            SELECT arc_name, arc_goal, arc_status, arc_progress
            FROM character_arcs
            WHERE character_id = $1
            ORDER BY id DESC
        """, character["id"])

        items = await conn.fetch("""
            SELECT item_name, item_type, item_description, quantity, equipped
            FROM inventory
            WHERE character_id = $1
            ORDER BY item_name
        """, character["id"])

        reputation = await conn.fetch("""
            SELECT kingdom, fame_level, notes
            FROM reputation
            WHERE character_id = $1
            ORDER BY kingdom
        """, character["id"])

        battle_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM battle_logs
            WHERE participants::text ILIKE $1
        """, f"%{name}%")

        return {
            "character": character,
            "arcs": arcs,
            "items": items,
            "reputation": reputation,
            "battle_count": battle_count
        }

# ---------- QUOTES ----------

async def save_quotes(day, quotes):
    if not quotes:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for character_name, quote in quotes:
            character_id = await conn.fetchval(
                "SELECT id FROM characters WHERE name = $1",
                character_name
            )
            await conn.execute("""
                INSERT INTO quotes (day, character_id, character_name, quote)
                VALUES ($1, $2, $3, $4)
            """, day, character_id, character_name, quote)

async def get_quotes(name=None, limit=5):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if name:
            return await conn.fetch("""
                SELECT day, character_name, quote
                FROM quotes
                WHERE character_name ILIKE $1
                ORDER BY id DESC
                LIMIT $2
            """, f"%{name}%", limit)

        return await conn.fetch("""
            SELECT day, character_name, quote
            FROM quotes
            ORDER BY id DESC
            LIMIT $1
        """, limit)

# ---------- INVENTORY ----------

async def apply_inventory_changes(gains, losses, day):
    pool = await get_pool()
    async with pool.acquire() as conn:
        for character_name, item_name, item_type, description in gains:
            character_id = await conn.fetchval(
                "SELECT id FROM characters WHERE name = $1",
                character_name
            )
            if not character_id:
                continue

            await conn.execute("""
                INSERT INTO inventory (character_id, item_name, item_type, item_description, obtained_day)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (character_id, item_name)
                DO UPDATE SET quantity = inventory.quantity + 1,
                              item_description = EXCLUDED.item_description
            """, character_id, item_name, item_type, description, day)

        for character_name, item_name in losses:
            character_id = await conn.fetchval(
                "SELECT id FROM characters WHERE name = $1",
                character_name
            )
            if not character_id:
                continue

            await conn.execute("""
                DELETE FROM inventory
                WHERE character_id = $1 AND item_name = $2
            """, character_id, item_name)

async def get_inventory(name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT i.item_name, i.item_type, i.item_description, i.quantity, i.equipped
            FROM inventory i
            JOIN characters c ON c.id = i.character_id
            WHERE c.name ILIKE $1
            ORDER BY i.item_name
        """, name)

async def get_inventory_for_prompt():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT c.name, i.item_name, i.item_type, i.item_description, i.quantity
            FROM inventory i
            JOIN characters c ON c.id = i.character_id
            ORDER BY c.name, i.item_name
        """)

# ---------- LOCATION / REPUTATION ----------

async def update_locations(locations):
    if not locations:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for character_name, kingdom in locations:
            await conn.execute("""
                UPDATE characters
                SET current_kingdom = $1
                WHERE name = $2
            """, kingdom, character_name)

async def apply_reputation_changes(changes):
    if not changes:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for character_name, kingdom, amount, notes in changes:
            character_id = await conn.fetchval(
                "SELECT id FROM characters WHERE name = $1",
                character_name
            )
            if not character_id:
                continue

            await conn.execute("""
                INSERT INTO reputation (character_id, kingdom, fame_level, notes)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (character_id, kingdom)
                DO UPDATE SET fame_level = reputation.fame_level + EXCLUDED.fame_level,
                              notes = COALESCE(EXCLUDED.notes, reputation.notes)
            """, character_id, kingdom, amount, notes)

async def get_reputation(name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT r.kingdom, r.fame_level, r.notes
            FROM reputation r
            JOIN characters c ON c.id = r.character_id
            WHERE c.name ILIKE $1
            ORDER BY r.fame_level DESC
        """, name)

async def get_character_locations():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT name, race, current_kingdom
            FROM characters
            WHERE status != 'Muerto'
            ORDER BY name
        """)

# ---------- NPCS ----------

async def upsert_npcs(npcs, day):
    if not npcs:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for name, race, role, kingdom, description in npcs:
            await conn.execute("""
                INSERT INTO npcs (name, race, role, kingdom, description, status, first_appearance_day, last_appearance_day)
                VALUES ($1, $2, $3, $4, $5, 'Active', $6, $6)
                ON CONFLICT (name)
                DO UPDATE SET race = COALESCE(EXCLUDED.race, npcs.race),
                              role = COALESCE(EXCLUDED.role, npcs.role),
                              kingdom = COALESCE(EXCLUDED.kingdom, npcs.kingdom),
                              description = COALESCE(EXCLUDED.description, npcs.description),
                              status = 'Active',
                              last_appearance_day = EXCLUDED.last_appearance_day
            """, name, race, role, kingdom, description, day)

async def mark_npcs_inactive(names, day):
    if not names:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for name in names:
            await conn.execute("""
                UPDATE npcs
                SET status = 'Inactive', last_appearance_day = $1
                WHERE name = $2
            """, day, name)

async def get_npcs(active_only=True):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if active_only:
            return await conn.fetch("""
                SELECT name, race, role, kingdom, description, status, first_appearance_day, last_appearance_day
                FROM npcs
                WHERE status = 'Active'
                ORDER BY name
            """)

        return await conn.fetch("""
            SELECT name, race, role, kingdom, description, status, first_appearance_day, last_appearance_day
            FROM npcs
            ORDER BY name
        """)

async def get_npc(name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT name, race, role, kingdom, description, status, first_appearance_day, last_appearance_day, notes
            FROM npcs
            WHERE name ILIKE $1
        """, name)

# ---------- BATTLES ----------

async def save_battles(day, battles):
    if not battles:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for participants, enemies, outcome, summary in battles:
            await conn.execute("""
                INSERT INTO battle_logs (day, participants, enemies, outcome, summary)
                VALUES ($1, $2::jsonb, $3::jsonb, $4, $5)
            """, day, json.dumps(participants), json.dumps(enemies), outcome, summary)

async def get_battles(name=None, limit=5):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if name:
            return await conn.fetch("""
                SELECT day, participants, enemies, outcome, summary
                FROM battle_logs
                WHERE participants::text ILIKE $1
                ORDER BY id DESC
                LIMIT $2
            """, f"%{name}%", limit)

        return await conn.fetch("""
            SELECT day, participants, enemies, outcome, summary
            FROM battle_logs
            ORDER BY id DESC
            LIMIT $1
        """, limit)
    
# ---------- VOTES ----------

async def create_vote(day, question, options, source="ai"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            INSERT INTO votes (day, question, options, status, source)
            VALUES ($1, $2, $3::jsonb, 'open', $4)
            RETURNING id
        """,
        day,
        question,
        json.dumps(options),
        source
        )

async def set_vote_message_id(vote_id: int, message_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE votes
            SET message_id = $1
            WHERE id = $2
        """, message_id, vote_id)

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
            "SELECT id, name FROM characters WHERE name ILIKE $1",
            name
        )

        if not row:
            return False  # personaje no existe

        character_id = row["id"]
        character_name = row["name"]

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

        death_text = f"{character_name} ha muerto definitivamente. Causa: {cause}"
        death_summary = f"Muerte permanente de {character_name}"

        await conn.execute("""
            INSERT INTO daily_logs (day, title, full_text, summary)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (day) DO UPDATE SET
                full_text = CONCAT_WS(E'\n\n', daily_logs.full_text, EXCLUDED.full_text),
                summary = CONCAT_WS(E'\n', daily_logs.summary, EXCLUDED.summary)
        """,
            day,
            "Muerte de un Campeón",
            death_text,
            death_summary
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
            SELECT id, question, options, message_id
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
        await conn.execute("DELETE FROM quotes")
        await conn.execute("DELETE FROM inventory")
        await conn.execute("DELETE FROM reputation")
        await conn.execute("DELETE FROM npcs")
        await conn.execute("DELETE FROM battle_logs")

        await conn.execute("""
            UPDATE characters
            SET status = 'Vivo',
                level = 1,
                current_kingdom = NULL,
                notes = NULL
        """)

        await conn.execute("""
            UPDATE world
            SET current_day = 0
            WHERE id = 1
        """)

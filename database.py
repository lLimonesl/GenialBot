import aiosqlite
import os
DB_PATH = os.getenv("DB_PATH", "isekai.db")

async def get_characters():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT name, race, status FROM characters WHERE status != 'Muerto' ")
        return await cursor.fetchall()

async def save_day(full_text: str, summary: str, title: str):
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        # Obtener día actual DENTRO de la misma conexión
        cur = await db.execute("SELECT current_day FROM world")
        row = await cur.fetchone()
        current_day = row[0]

        new_day = current_day + 1

        # Guardar día
        await db.execute(
            """
            INSERT INTO daily_logs (day, title, full_text, summary)
            VALUES (?, ?, ?, ?)
            """,
            (new_day, title, full_text, summary)
        )

        # Actualizar mundo
        await db.execute(
            "UPDATE world SET current_day = ?",
            (new_day,)
        )

        await db.commit()

        return new_day
    
async def day_exists(day):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM daily_logs WHERE day = ?", (day,)
        )
        return await cur.fetchone() is not None
    
async def ensure_initial_arcs():
    characters = await get_characters()

    async with aiosqlite.connect(DB_PATH) as db:
        for name, _, _ in characters:
            cur = await db.execute("""
            SELECT 1 FROM character_arcs
            WHERE character_name = ?
            """, (name,))
            exists = await cur.fetchone()

            if not exists:
                await db.execute("""
                INSERT INTO character_arcs
                (character_name, arc_name, arc_goal, arc_status, arc_progress)
                VALUES (?, ?, ?, 'active', 0)
                """, (
                    name,
                    "Despertar en un Mundo Desconocido",
                    "Sobrevivir, adaptarse y entender su rol en el reino"
                ))

        await db.commit()
    
async def init_arcs():
    async with aiosqlite.connect("isekai.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS character_arcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT,
            arc_name TEXT,
            arc_goal TEXT,
            arc_status TEXT,
            arc_progress INTEGER
        )
        """)
        await db.commit()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabla del mundo (día actual)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS world (
            current_day INTEGER
        )
        """)

        # Asegurar fila inicial
        cur = await db.execute("SELECT COUNT(*) FROM world")
        count = (await cur.fetchone())[0]
        if count == 0:
            await db.execute("INSERT INTO world VALUES (0)")

        # Logs diarios
        await db.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day INTEGER,
            title TEXT,
            full_text TEXT,
            summary TEXT
        )
        """)

        # Personajes
        await db.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            name TEXT PRIMARY KEY,
            race TEXT,
            status TEXT
        )
        """)

        await db.commit()

    await init_arcs()
    await ensure_initial_arcs()
    await init_votes()
    await init_pov()

async def create_initial_arc(name):
    async with aiosqlite.connect("isekai.db") as db:
        await db.execute("""
        INSERT INTO character_arcs
        (character_name, arc_name, arc_goal, arc_status, arc_progress)
        VALUES (?, ?, ?, 'active', 0)
        """, (
            name,
            "Despertar en el Mundo Desconocido",
            "Sobrevivir y entender las reglas del nuevo mundo"
        ))
        await db.commit()

async def get_active_arcs():
    async with aiosqlite.connect("isekai.db") as db:
        cursor = await db.execute("""
        SELECT character_name, arc_name, arc_goal, arc_progress
        FROM character_arcs
        WHERE arc_status = 'active'
        """)
        return await cursor.fetchall()

async def advance_arc(character, amount):
    async with aiosqlite.connect("isekai.db") as db:
        await db.execute("""
        UPDATE character_arcs
        SET arc_progress = MIN(100, arc_progress + ?)
        WHERE character_name = ? AND arc_status = 'active'
        """, (amount, character))
        await db.commit()

async def close_completed_arcs():
    async with aiosqlite.connect("isekai.db") as db:
        await db.execute("""
        UPDATE character_arcs
        SET arc_status = 'closed'
        WHERE arc_progress >= 100
        """)
        await db.commit()

async def set_character_status(name: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE characters
        SET status = ?
        WHERE name = ?
        """, (status, name))
        await db.commit()

async def kill_character(name: str, cause: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Marcar como muerto
        await db.execute("""
        UPDATE characters
        SET status = 'Muerto'
        WHERE name = ?
        """, (name,))

        # Cerrar su arco
        await db.execute("""
        UPDATE character_arcs
        SET arc_status = 'closed'
        WHERE character_name = ?
        """, (name,))

        # Registrar evento irreversible
        await db.execute("""
        INSERT INTO daily_logs (day, title, full_text, summary)
        VALUES (
            (SELECT current_day FROM world),
            'Muerte de un Campeón',
            ?,
            ?
        )
        """, (
            f"{name} ha muerto definitivamente. Causa: {cause}",
            f"Muerte permanente de {name}"
        ))

        await db.commit()

async def init_votes():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day INTEGER,
            question TEXT,
            options TEXT,
            result TEXT,
            status TEXT
        )
        """)
        await db.commit()

async def create_vote(day, question, options):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO votes (day, question, options, status)
        VALUES (?, ?, ?, 'open')
        """, (day, question, ",".join(options)))
        await db.commit()

async def close_vote(vote_id, result):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE votes
        SET result = ?, status = 'closed'
        WHERE id = ?
        """, (result, vote_id))
        await db.commit()

async def get_closed_votes(limit=3):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        SELECT question, result
        FROM votes
        WHERE status = 'closed'
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        return await cur.fetchall()
    
async def init_pov():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS pov_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_pov TEXT
        )
        """)
        # Asegurar fila única
        cur = await db.execute("SELECT COUNT(*) FROM pov_state")
        if (await cur.fetchone())[0] == 0:
            await db.execute(
                "INSERT INTO pov_state (id, current_pov) VALUES (1, NULL)"
            )
        await db.commit()

async def get_current_pov():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT current_pov FROM pov_state WHERE id = 1"
        )
        row = await cur.fetchone()
        return row[0]
    
async def set_pov(name: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pov_state SET current_pov = ? WHERE id = 1",
            (name,)
        )
        await db.commit()

async def rotate_pov():
    characters = await get_characters()
    alive = [c[0] for c in characters]

    current = await get_current_pov()
    if not alive:
        return None

    if current not in alive:
        return alive[0]

    idx = alive.index(current)
    return alive[(idx + 1) % len(alive)]
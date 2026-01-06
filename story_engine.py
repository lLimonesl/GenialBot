import os
import aiosqlite
from dotenv import load_dotenv
from openai import OpenAI
from database import get_characters
from database import get_closed_votes
from database import get_active_arcs
from database import get_current_pov

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_PATH = "isekai.db"


async def get_world_state():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT current_day, rules FROM world LIMIT 1")
        return await cur.fetchone()


async def get_recent_events(limit=5):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT summary FROM daily_logs ORDER BY day DESC LIMIT ?", (limit,)
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def generate_next_day():
    world_day, rules = await get_world_state()
    characters = await get_characters()
    recent = await get_recent_events()

    char_text = "\n".join([f"- {c[0]} ({c[1]})" for c in characters])
    recent_text = "\n".join(recent) if recent else "Aún no hay eventos."

    arcs = await get_active_arcs()
    votes = await get_closed_votes()
    pov = await get_current_pov()

    if pov:
        pov_text = f"""
    POV ACTUAL: {pov}

    Narración:
    - Escrita en tercera persona limitada
    - Solo muestra lo que {pov} puede ver, oír o deducir
    - Pensamientos internos permitidos
    - Información fuera de su alcance NO debe aparecer
    """
    else:
        pov_text = """
    POV ACTUAL: Narrador omnisciente
    """

    vote_context = "\n".join([
        f"Decisión del público: {q} → {r}"
        for q, r in votes
    ])

    arc_context = "\n".join([
        f"{name}: Arco '{arc}' | Objetivo: {goal} | Progreso: {progress}%"
        for name, arc, goal, progress in arcs
    ])

    prompt = f"""
Eres el narrador de una historia isekai oscura y coherente.

Arcos narrativos activos por personaje:
{arc_context}

Reglas narrativas:
- NO avances todos los arcos en un mismo día
- Prioriza máximo 2 personajes por día
- Los demás siguen en segundo plano
- El progreso es lento y coherente
- Un arco solo avanza si el personaje actúa directamente

{pov_text}

Reglas de muerte:
- Los personajes pueden morir si la situación lo amerita
- La muerte es permanente
- Personajes muertos NO vuelven a actuar
- Mascotas solo reviven si su lore lo permite
- La muerte impacta al reino, al arco y al mundo

Decisiones tomadas por los observadores (votaciones):
{vote_context}

Reglas:
- Las decisiones del público SON CANÓN
- No contradigas una votación cerrada
- Narra consecuencias directas

Reglas del mundo:
{rules}

Personajes activos:
{char_text}

Eventos pasados:
{recent_text}

Día actual: {world_day}

Instrucciones:
- Genera SOLO el día {world_day + 1}
- No repitas eventos
- Respeta poderes y jerarquía racial
- El mundo reacciona según la raza
- Mantén consecuencias permanentes

Formato:
Título del día
Narrativa
Resumen corto
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )

    return response.choices[0].message.content

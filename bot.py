import os
import discord
from discord.ext import commands, tasks
from database import init_db, save_day
from story_engine import generate_next_day
from dotenv import load_dotenv
from db import get_pool
from database import get_characters
from database import init_db
from database import get_active_arcs
from database import kill_character
from database import create_vote, get_current_day
from database import close_vote
from database import get_current_pov
from database import set_pov
from database import save_day

# Cargar variables de entorno
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Intents necesarios
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def split_message(text, limit=1900):
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:]
    parts.append(text)
    return parts

@bot.event
async def on_ready():
    await init_db()
    if not daily_story_task.is_running():
        daily_story_task.start()
    print(f"Bot conectado como {bot.user}")

@tasks.loop(hours=24)
async def daily_story_task():
    channel_id = int(os.getenv("STORY_CHANNEL_ID"))
    channel = bot.get_channel(channel_id)

    if channel is None:
        print("Canal no encontrado")
        return

    texto = await generate_next_day()

    lines = texto.split("\n", 1)
    title = lines[0].strip()
    summary = texto[:200]

    new_day = await save_day(
        full_text=texto,
        summary=summary,
        title=title
    )

    header = f"**Día {new_day}: {title}**\n"
    chunks = split_message(header + texto)

    for part in chunks:
        await channel.send(part)

# Comando de prueba
@bot.command()
async def ping(ctx):
    await ctx.send("Pong! El narrador ha despertado.")

@bot.command()
async def personajes(ctx):
    chars = await get_characters()
    msg = "\n".join([f"{c[0]} ({c[1]}) - {c[2]}" for c in chars])
    await ctx.send(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def matar(ctx, nombre: str, *, causa="Destino del mundo"):
    ok = await kill_character(nombre, causa)
    if ok:
        await ctx.send(f"☠️ **{nombre} ha muerto definitivamente.**\nCausa: {causa}")
    else:
        await ctx.send("❌ Personaje no encontrado.")

@bot.command()
async def arcos(ctx):
    arcs = await get_active_arcs()
    if not arcs:
        await ctx.send("No hay arcos activos.")
        return

    msg = "**Arcos activos:**\n"
    for name, arc, goal, progress in arcs:
        msg += f"• {name}: {arc} ({progress}%)\n"
    await ctx.send(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def votar(ctx, *, pregunta_opciones: str):
    """
    Ejemplo:
    !votar ¿El reino esclaviza a Alex?|Sí|No
    """
    parts = pregunta_opciones.split("|")
    if len(parts) < 3:
        await ctx.send("Formato: pregunta|opcion1|opcion2|...")
        return

    question = parts[0]
    options = parts[1:]

    day = await get_current_day()
    await create_vote(day, question, options)

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    msg = f"🗳️ **VOTACIÓN ABIERTA (Día {day})**\n{question}\n"

    for i, opt in enumerate(options):
        msg += f"{emojis[i]} {opt}\n"

    poll = await ctx.send(msg)

    for i in range(len(options)):
        await poll.add_reaction(emojis[i])

@bot.command()
@commands.has_permissions(administrator=True)
async def cerrar_votacion(ctx, vote_id: int, *, resultado: str):
    await close_vote(vote_id, resultado)
    await ctx.send(f"✅ Votación {vote_id} cerrada.\nResultado: {resultado}")

@bot.command()
async def pov(ctx):
    pov = await get_current_pov()
    if pov:
        await ctx.send(f"👁️ POV actual: **{pov}**")
    else:
        await ctx.send("👁️ POV actual: Narrador omnisciente")

@bot.command()
async def dbtest(ctx):
    pool = await get_pool()
    async with pool.acquire() as conn:
        day = await conn.fetchval(
            "SELECT current_day FROM world WHERE id = 1"
        )
    await ctx.send(f"✅ PostgreSQL conectado correctamente. Día actual: {day}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setpov(ctx, nombre: str):
    await set_pov(nombre)
    await ctx.send(f"👁️ POV fijado en **{nombre}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def clearpov(ctx):
    await set_pov(None)
    await ctx.send("👁️ POV restablecido a narrador omnisciente")

@bot.command()
async def generar_dia(ctx):
    texto = await generate_next_day()

    lines = texto.split("\n", 1)
    title = lines[0].strip()
    summary = texto[:200]

    new_day = await save_day(
        full_text=texto,
        summary=summary,
        title=title
    )

    header = f"**Día {new_day}: {title}**\n"
    chunks = split_message(header + texto)

    for part in chunks:
        await ctx.send(part)

bot.run(TOKEN)

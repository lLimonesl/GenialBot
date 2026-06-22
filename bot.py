import os
import json
import discord
from discord.ext import commands, tasks
from database import init_db
from story_engine import generate_next_day, detect_critical_decision
from dotenv import load_dotenv
from db import get_pool
from database import get_characters
from database import get_active_arcs
from database import kill_character
from database import create_vote, get_current_day
from database import get_open_votes_older_than, close_vote, set_vote_message_id
from database import reset_world_progress
from database import get_character_stats, get_day_log, search_logs_by_character
from database import get_inventory, get_quotes, get_reputation, get_character_locations
from database import get_npcs, get_npc, get_battles
from pdf_exporter import export_day_to_pdf

# Cargar variables de entorno
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or os.getenv("STORY_CHANNEL_ID"))

# Intents necesarios
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

RAW_METADATA_PREFIXES = (
    "[WEATHER]",
    "[QUOTE]",
    "[ITEM_GAIN]",
    "[ITEM_LOSE]",
    "[LOCATION]",
    "[FAME]",
    "[NEW_ARC]",
    "[ARC_PROGRESS]",
    "[NPC_APPEAR]",
    "[NPC_DISAPPEAR]",
    "[BATTLE]",
    "[LEVEL_UP]"
)

def hide_raw_metadata_tags(text):
    lines = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("-*>` ").strip()
        if stripped.startswith(RAW_METADATA_PREFIXES):
            continue
        lines.append(line)
    return "\n".join(lines).strip()

async def send_long_message(channel_id, text):
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    text = hide_raw_metadata_tags(text)

    max_length = 2000
    for i in range(0, len(text), max_length):
        await channel.send(text[i:i + max_length])

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

def format_json_value(value):
    if value is None:
        return "N/A"
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return json.dumps(parsed, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)

async def send_split(ctx, text):
    for part in split_message(text):
        await ctx.send(part)

async def send_commands_help(ctx):
    msg = """
**Comandos disponibles**

**Historia**
• `!generar_dia` - Genera manualmente el siguiente día
• `!historial` - Muestra el día actual guardado
• `!historial <día>` - Muestra un día específico
• `!historial --personaje <nombre>` - Busca días donde aparece un personaje

**Personajes**
• `!personajes` - Lista personajes vivos
• `!stats <personaje>` - Perfil, nivel, equipo, arcos, fama y combates
• `!inventario <personaje>` - Inventario actual
• `!mapa` - Ubicación actual de personajes
• `!fama <personaje>` - Reputación por reino

**Mundo**
• `!arcos` - Arcos activos
• `!citas [personaje]` - Citas memorables
• `!npcs` - NPCs activos
• `!npc <nombre>` - Detalle de un NPC
• `!combates [personaje]` - Combates registrados

**Votaciones**
• `!votar pregunta|opción1|opción2|...` - Crea votación manual (admin)
• `!cerrar_votacion <id> <resultado>` - Cierra una votación (admin)

**Administración**
• `!matar <nombre> [causa]` - Muerte permanente (admin)
• `!resetear_mundo` - Reinicia progreso narrativo (admin)
• `!dbtest` - Prueba conexión PostgreSQL
""".strip()
    await send_split(ctx, msg)

async def count_reactions(message):
    results = {}
    for reaction in message.reactions:
        if reaction.emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:
            results[str(reaction.emoji)] = reaction.count - 1
    return results

def decode_vote_options(options):
    if isinstance(options, str):
        return json.loads(options)
    return options

async def publish_critical_decision(channel, day, texto):
    decision = await detect_critical_decision(texto)

    if not decision:
        return

    options = decision.get("options", [])[:4]
    if len(options) < 2:
        return

    msg = f"🗳️ **DECISIÓN CRÍTICA (Día {day})**\n"
    msg += decision["question"] + "\n"

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for i, opt in enumerate(options):
        msg += f"{emojis[i]} {opt}\n"

    poll = await channel.send(msg)
    vote_id = await create_vote(day, decision["question"], options, source="ai")
    await set_vote_message_id(vote_id, poll.id)

    for i in range(len(options)):
        await poll.add_reaction(emojis[i])

@tasks.loop(minutes=30)
async def close_votes_task():
    votes = await get_open_votes_older_than(15)

    if not votes:
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for vote in votes:
        if vote["message_id"]:
            try:
                message = await channel.fetch_message(vote["message_id"])
            except discord.NotFound:
                message = None
        else:
            message = None
            async for candidate in channel.history(limit=200):
                if vote["question"] in candidate.content:
                    message = candidate
                    break

        if not message:
            continue

        counts = await count_reactions(message)

        if not counts or max(counts.values()) <= 0:
            result = "Sin votos"
        else:
            options = decode_vote_options(vote["options"])
            winner = max(counts, key=counts.get)
            index = emojis.index(winner)
            result = options[index]

        await close_vote(vote["id"], result)

        await channel.send(
            f"🗳️ **VOTACIÓN CERRADA**\n"
            f"Pregunta: {vote['question']}\n"
            f"Resultado: **{result}**"
        )

@bot.event
async def on_ready():
    await init_db()

    if not daily_story_task.is_running():
        daily_story_task.start()

    if not close_votes_task.is_running():
        close_votes_task.start()

    print(f"Bot conectado como {bot.user}")

@tasks.loop(hours=24)
async def daily_story_task():
    clean_text, display_text, title = await generate_next_day()

    # Enviar historia
    await send_long_message(CHANNEL_ID, f"**{title}**\n{display_text}")

    # Día actual
    day = await get_current_day()

    # Exportar PDF
    from pdf_exporter import export_day_to_pdf
    pdf_path = export_day_to_pdf(day, title, clean_text)

    channel = bot.get_channel(CHANNEL_ID)

    # Enviar PDF
    await channel.send(
        content=f"📄 **Archivo del Día {day}**",
        file=discord.File(pdf_path)
    )

    await publish_critical_decision(channel, day, clean_text)


# Comando de prueba
@bot.command()
async def ping(ctx):
    await ctx.send("Pong! El narrador ha despertado.")

@bot.command()
async def comandos(ctx):
    await send_commands_help(ctx)

@bot.command(name="help")
async def help_command(ctx):
    await send_commands_help(ctx)

@bot.command()
async def personajes(ctx):
    chars = await get_characters()
    msg = "\n".join([f"{c[0]} ({c[1]}) - {c[2]}" for c in chars])
    await ctx.send(msg)

@bot.command()
async def stats(ctx, *, nombre: str):
    data = await get_character_stats(nombre)
    if not data:
        await ctx.send("❌ Personaje no encontrado.")
        return

    c = data["character"]
    msg = f"**Stats de {c['name']}**\n"
    msg += f"Raza: {c['race']} | Estado: {c['status']} | Nivel: {c['level']}\n"
    msg += f"Estatus social: {c['social_status']}\n"
    msg += f"Ubicación: {c['current_kingdom'] or 'Desconocida'}\n"
    msg += f"Arma inicial: {c['weapon'] or 'N/A'}\n"
    msg += f"Amuleto inicial: {c['amulet'] or 'N/A'}\n"
    msg += f"Mascota: {format_json_value(c['pet'])}\n"
    msg += f"Habilidades: {format_json_value(c['abilities'])}\n"
    msg += f"Pasivas: {format_json_value(c['passives'])}\n"
    msg += f"Movimiento final: {format_json_value(c['final_move'])}\n"
    msg += f"Combates registrados: {data['battle_count']}\n"

    if data["arcs"]:
        msg += "\n**Arcos:**\n"
        for arc in data["arcs"][:5]:
            msg += f"• {arc['arc_name']} ({arc['arc_status']}, {arc['arc_progress']}%): {arc['arc_goal']}\n"

    if data["items"]:
        msg += "\n**Inventario:**\n"
        for item in data["items"][:8]:
            msg += f"• {item['item_name']} x{item['quantity']} ({item['item_type'] or 'sin tipo'})\n"

    if data["reputation"]:
        msg += "\n**Fama:**\n"
        for rep in data["reputation"][:5]:
            msg += f"• {rep['kingdom']}: {rep['fame_level']}\n"

    await send_split(ctx, msg)

@bot.command()
async def historial(ctx, *args):
    if args and args[0] == "--personaje":
        nombre = " ".join(args[1:]).strip()
        if not nombre:
            await ctx.send("Formato: `!historial --personaje <nombre>`")
            return

        rows = await search_logs_by_character(nombre)
        if not rows:
            await ctx.send("No encontré entradas para ese personaje.")
            return

        msg = f"**Historial de {nombre}:**\n"
        for row in rows:
            weather = f" | Clima: {row['weather']}" if row['weather'] else ""
            msg += f"• Día {row['day']} - {row['title'] or 'Sin título'}{weather}\n{row['summary'] or 'Sin resumen'}\n"
        await send_split(ctx, msg)
        return

    try:
        day = int(args[0]) if args else await get_current_day()
    except ValueError:
        await ctx.send("Formato: `!historial [día]` o `!historial --personaje <nombre>`")
        return
    row = await get_day_log(day)
    if not row:
        await ctx.send("No encontré ese día en el diario.")
        return

    weather = f"\nClima: {row['weather']}" if row['weather'] else ""
    await send_split(ctx, f"**{row['title'] or f'Día {day}'}**{weather}\n{row['full_text'] or row['summary']}")

@bot.command()
async def inventario(ctx, *, nombre: str):
    items = await get_inventory(nombre)
    if not items:
        await ctx.send("No hay inventario registrado para ese personaje.")
        return

    msg = f"**Inventario de {nombre}:**\n"
    for item in items:
        equipped = " equipado" if item["equipped"] else ""
        msg += f"• {item['item_name']} x{item['quantity']} ({item['item_type'] or 'sin tipo'}){equipped}: {item['item_description'] or 'Sin descripción'}\n"
    await send_split(ctx, msg)

@bot.command()
async def citas(ctx, *, nombre: str = None):
    rows = await get_quotes(nombre)
    if not rows:
        await ctx.send("No hay citas registradas.")
        return

    msg = "**Citas memorables:**\n"
    for row in rows:
        msg += f"• Día {row['day']} - {row['character_name']}: \"{row['quote']}\"\n"
    await send_split(ctx, msg)

@bot.command()
async def mapa(ctx):
    rows = await get_character_locations()
    msg = "**Mapa actual:**\n"
    for row in rows:
        msg += f"• {row['name']} ({row['race']}): {row['current_kingdom'] or 'Ubicación desconocida'}\n"
    await send_split(ctx, msg)

@bot.command()
async def fama(ctx, *, nombre: str):
    rows = await get_reputation(nombre)
    if not rows:
        await ctx.send("No hay fama registrada para ese personaje.")
        return

    msg = f"**Fama de {nombre}:**\n"
    for row in rows:
        notes = f" - {row['notes']}" if row["notes"] else ""
        msg += f"• {row['kingdom']}: {row['fame_level']}{notes}\n"
    await send_split(ctx, msg)

@bot.command()
async def npcs(ctx):
    rows = await get_npcs(active_only=True)
    if not rows:
        await ctx.send("No hay NPCs activos registrados.")
        return

    msg = "**NPCs activos:**\n"
    for row in rows:
        msg += f"• {row['name']} ({row['race'] or 'N/A'}) - {row['role'] or 'sin rol'} en {row['kingdom'] or 'ubicación desconocida'}\n"
    await send_split(ctx, msg)

@bot.command()
async def npc(ctx, *, nombre: str):
    row = await get_npc(nombre)
    if not row:
        await ctx.send("NPC no encontrado.")
        return

    msg = f"**{row['name']}**\n"
    msg += f"Raza: {row['race'] or 'N/A'} | Rol: {row['role'] or 'N/A'} | Estado: {row['status']}\n"
    msg += f"Ubicación: {row['kingdom'] or 'Desconocida'}\n"
    msg += f"Primera aparición: Día {row['first_appearance_day'] or 'N/A'} | Última: Día {row['last_appearance_day'] or 'N/A'}\n"
    msg += row['description'] or 'Sin descripción'
    await send_split(ctx, msg)

@bot.command()
async def combates(ctx, *, nombre: str = None):
    rows = await get_battles(nombre)
    if not rows:
        await ctx.send("No hay combates registrados.")
        return

    msg = "**Combates registrados:**\n"
    for row in rows:
        participants = format_json_value(row['participants'])
        enemies = format_json_value(row['enemies'])
        msg += f"• Día {row['day']} | {row['outcome']}\nParticipantes: {participants}\nEnemigos: {enemies}\n{row['summary']}\n"
    await send_split(ctx, msg)

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

    if len(options) > 5:
        await ctx.send("Máximo 5 opciones por votación.")
        return

    day = await get_current_day()

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    msg = f"🗳️ **VOTACIÓN ABIERTA (Día {day})**\n{question}\n"

    for i, opt in enumerate(options):
        msg += f"{emojis[i]} {opt}\n"

    poll = await ctx.send(msg)
    vote_id = await create_vote(day, question, options, source="manual")
    await set_vote_message_id(vote_id, poll.id)

    for i in range(len(options)):
        await poll.add_reaction(emojis[i])

@bot.command()
@commands.has_permissions(administrator=True)
async def cerrar_votacion(ctx, vote_id: int, *, resultado: str):
    await close_vote(vote_id, resultado)
    await ctx.send(f"✅ Votación {vote_id} cerrada.\nResultado: {resultado}")

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
async def resetear_mundo(ctx):
    await reset_world_progress()
    await ctx.send(
        "🔄 **MUNDO REINICIADO**\n"
        "• Día vuelto a 0\n"
        "• Historia borrada\n"
        "• Votaciones borradas\n"
        "• Inventario, fama, NPCs, combates y arcos borrados\n"
        "• Personajes restaurados a vivos, nivel 1 y sin ubicación actual\n"
        "Las reglas del mundo permanecen intactas."
    )

@bot.command()
async def generar_dia(ctx):
    clean_text, display_text, title = await generate_next_day()

    # Enviar historia (maneja +2000 chars)
    await send_long_message(CHANNEL_ID, f"**{title}**\n{display_text}")

    # Obtener día actual (ya incrementado)
    day = await get_current_day()

    # Exportar a PDF
    from pdf_exporter import export_day_to_pdf
    pdf_path = export_day_to_pdf(day, title, clean_text)

    # Enviar PDF
    await ctx.send(
        content=f"📄 **Archivo del Día {day}**",
        file=discord.File(pdf_path)
    )

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await publish_critical_decision(channel, day, clean_text)


bot.run(TOKEN)

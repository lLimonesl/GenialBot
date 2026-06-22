import os
import json
import random
import asyncio
import discord
from discord.ext import commands, tasks
from database import init_db
from story_engine import generate_next_day, detect_critical_decision, suggest_abilities_for_level_up
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
from database import get_power_ranking, record_consequence, get_votes, get_active_key_events
from database import get_quotes_for_day, create_ability_unlock_vote, apply_unlocked_ability, get_vote
from database import trade_item, get_recent_trades
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
dashboard_started = False

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
    "[LEVEL_UP]",
    "[KEY_EVENT]",
    "[SEASON]"
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

def quote_tokens(text):
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {word for word in cleaned.split() if len(word) > 3}

def quotes_are_similar(left, right):
    left_tokens = quote_tokens(left)
    right_tokens = quote_tokens(right)
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    return overlap / min(len(left_tokens), len(right_tokens)) >= 0.55

def select_featured_quote(quotes, recent_quotes, day):
    previous_quotes = [q for q in recent_quotes if q["day"] != day]
    recent_characters = {q["character_name"] for q in previous_quotes[:12]}

    fresh_quotes = []
    for quote in quotes:
        if quote["character_name"] in recent_characters:
            continue
        if any(quotes_are_similar(quote["quote"], previous["quote"]) for previous in previous_quotes[:12]):
            continue
        fresh_quotes.append(quote)

    if fresh_quotes:
        return random.choice(fresh_quotes)

    non_repeated_character = [q for q in quotes if q["character_name"] not in recent_characters]
    if non_repeated_character:
        return random.choice(non_repeated_character)

    return None

async def send_split(ctx, text):
    for part in split_message(text):
        await ctx.send(part)

def remove_file_safely(path):
    try:
        os.remove(path)
    except OSError:
        pass

async def send_commands_help(ctx):
    msg = """
**Comandos disponibles**

**Historia**
• `!generar_dia` - Testing: cierra votos abiertos con reacciones actuales y genera el siguiente día
• `!historial` - Muestra el día actual guardado
• `!historial <día>` - Muestra un día específico
• `!historial --personaje <nombre>` - Busca días donde aparece un personaje

**Personajes**
• `!personajes` - Lista personajes vivos
• `!stats <personaje>` - Perfil, nivel, equipo, arcos, fama y combates
• `!ranking` - Marcador de poder por nivel, fama y victorias
• `!inventario <personaje>` - Inventario actual
• `!mapa` - Ubicación actual de personajes
• `!fama <personaje>` - Reputación por reino

**Mundo**
• `!arcos` - Arcos activos
• `!citas [personaje]` - Citas memorables
• `!npcs` - NPCs activos
• `!npc <nombre>` - Detalle de un NPC
• `!combates [personaje]` - Combates registrados
• `!eventos` - Eventos clave activos del mundo
• `!comerciar personaje|reino destino|objeto` - Comercio simple de objeto
• `!comercio` - Últimos comercios registrados

**Votaciones**
• `!encuesta pregunta|opción1|opción2|...` - Encuesta rápida
• `!votar pregunta|opción1|opción2|...` - Crea votación manual (admin)
• `!cerrar_votacion <id> <resultado>` - Cierra una votación (admin)
• `!votaciones [abiertas|cerradas]` - Lista votaciones
• `!consecuencia <id> <texto>` - Guarda consecuencia visible (admin)

**Administración**
• `!matar <nombre> [causa]` - Muerte permanente (admin)
• `!resetear_mundo` - Reinicia progreso narrativo (admin)
• `!exportar_novela` - Genera HTML de la novela (admin)
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

def normalize_vote_option(text):
    return " ".join(str(text or "").strip().lower().split())

def option_is_valid(result, options):
    normalized = normalize_vote_option(result)
    return any(normalize_vote_option(option) == normalized for option in options)

def is_non_choice_result(result):
    normalized = normalize_vote_option(result)
    return (
        not normalized
        or normalized in {"sin votos", "sin resultado", "ninguna"}
        or normalized.startswith("empate")
    )

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

async def close_pending_votes_for_manual_generation(channel):
    if not channel:
        return []

    open_votes = await get_votes(status="open", limit=50)
    if not open_votes:
        return []

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    closed = []

    for vote in open_votes:
        message = None
        if vote["message_id"]:
            try:
                message = await channel.fetch_message(vote["message_id"])
            except discord.NotFound:
                message = None

        if not message:
            async for candidate in channel.history(limit=200):
                if vote["question"] in candidate.content:
                    message = candidate
                    break

        if not message:
            continue

        counts = await count_reactions(message)
        options = decode_vote_options(vote["options"])
        if not counts or max(counts.values()) <= 0:
            result = "Sin votos"
            tied = []
        else:
            max_votes = max(counts.values())
            tied = [emoji for emoji, count in counts.items() if count == max_votes]
            if len(tied) == 1:
                index = emojis.index(tied[0])
                result = options[index] if index < len(options) else "Sin resultado"
            else:
                tied_options = []
                for emoji in tied:
                    index = emojis.index(emoji)
                    if index < len(options):
                        tied_options.append(options[index])
                result = "Empate: " + " / ".join(tied_options)

        await close_vote(vote["id"], result)

        ability_message = ""
        if vote["vote_type"] == "ability" and not tied and option_is_valid(result, options) and not is_non_choice_result(result):
            character_name = await apply_unlocked_ability(vote["id"], result)
            if character_name:
                ability_message = f" | {character_name} desbloqueó habilidad"

        closed.append(f"#{vote['id']} {vote['question']} → {result}{ability_message}")

    return closed

async def publish_ability_votes(channel, day, level_ups):
    if not channel or not level_ups:
        return

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    for character_name, _amount in level_ups:
        abilities = await suggest_abilities_for_level_up(character_name)
        if not abilities:
            continue
        options = abilities[:3] + ["Ninguna"]
        msg = f"⬆️ **NUEVA HABILIDAD DISPONIBLE (Día {day})**\n"
        msg += f"{character_name} ha subido de nivel. ¿Qué habilidad desbloquea?\n"
        for i, option in enumerate(options):
            if ":" in option and option != "Ninguna":
                name, description = option.split(":", 1)
                msg += f"{emojis[i]} **{name.strip()}**: {description.strip()}\n"
            else:
                msg += f"{emojis[i]} {option}\n"

        poll = await channel.send(msg)
        vote_id = await create_vote(
            day,
            f"Habilidad desbloqueable para {character_name}",
            options,
            source="ability",
            vote_type="ability",
            close_after_hours=15
        )
        await set_vote_message_id(vote_id, poll.id)
        await create_ability_unlock_vote(character_name, day, options, vote_id)

        for i in range(len(options)):
            await poll.add_reaction(emojis[i])

async def publish_quote_of_day(channel, day):
    if not channel:
        return
    quotes = await get_quotes_for_day(day)
    if not quotes:
        return
    recent_quotes = await get_quotes(limit=20)
    quote = select_featured_quote(quotes, recent_quotes, day)
    if not quote:
        return
    await channel.send(
        f"💬 **Cita destacada del Día {day}**\n"
        f"*\"{quote['quote']}\"* — {quote['character_name']}"
    )

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
            max_votes = max(counts.values())
            tied = [emoji for emoji, count in counts.items() if count == max_votes]

            if len(tied) > 1 and not vote["parent_vote_id"]:
                tied_options = []
                for emoji in tied:
                    index = emojis.index(emoji)
                    if index < len(options):
                        tied_options.append(options[index])

                runoff_msg = f"🔁 **SEGUNDA VUELTA (Día {vote['day']})**\n{vote['question']}\n"
                for i, option in enumerate(tied_options):
                    runoff_msg += f"{emojis[i]} {option}\n"

                runoff = await channel.send(runoff_msg)
                runoff_id = await create_vote(
                    vote["day"],
                    vote["question"],
                    tied_options,
                    source="runoff",
                    vote_type="runoff",
                    close_after_hours=6,
                    parent_vote_id=vote["id"]
                )
                await set_vote_message_id(runoff_id, runoff.id)
                for i in range(len(tied_options)):
                    await runoff.add_reaction(emojis[i])
                await close_vote(vote["id"], "Empate - segunda vuelta creada")
                await channel.send("🔁 Hubo empate. Se abrió una segunda vuelta con las opciones empatadas.")
                continue

            winner = max(counts, key=counts.get)
            index = emojis.index(winner)
            result = options[index] if index < len(options) else "Sin resultado"

        await close_vote(vote["id"], result)

        ability_message = ""
        options = decode_vote_options(vote["options"])
        if vote["vote_type"] == "ability" and option_is_valid(result, options) and not is_non_choice_result(result):
            character_name = await apply_unlocked_ability(vote["id"], result)
            if character_name:
                ability_message = f"\n✨ {character_name} desbloqueó: **{result}**"

        await channel.send(
            f"🗳️ **VOTACIÓN CERRADA**\n"
            f"Pregunta: {vote['question']}\n"
            f"Resultado: **{result}**{ability_message}"
        )

@bot.event
async def on_ready():
    global dashboard_started
    await init_db()

    if not daily_story_task.is_running():
        daily_story_task.start()

    if not close_votes_task.is_running():
        close_votes_task.start()

    if not dashboard_started:
        dashboard_started = True
        asyncio.create_task(start_dashboard())

    print(f"Bot conectado como {bot.user}")

async def start_dashboard():
    try:
        import uvicorn
        from dashboard import app
        port = int(os.getenv("PORT", "8000"))
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except Exception as exc:
        print(f"Dashboard no iniciado: {exc}")

@tasks.loop(hours=24)
async def daily_story_task():
    clean_text, display_text, title, level_ups = await generate_next_day()

    # Enviar historia
    await send_long_message(CHANNEL_ID, f"**{title}**\n{display_text}")

    # Día actual
    day = await get_current_day()

    # Exportar PDF
    from pdf_exporter import export_day_to_pdf
    pdf_path = export_day_to_pdf(day, title, clean_text)

    channel = bot.get_channel(CHANNEL_ID)

    # Enviar PDF y borrar archivo temporal local.
    try:
        await channel.send(
            content=f"📄 **Archivo del Día {day}**",
            file=discord.File(pdf_path)
        )
    finally:
        remove_file_safely(pdf_path)

    await publish_critical_decision(channel, day, clean_text)
    await publish_ability_votes(channel, day, level_ups)
    await publish_quote_of_day(channel, day)


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
async def ranking(ctx):
    rows = await get_power_ranking()
    if not rows:
        await ctx.send("No hay personajes vivos para rankear.")
        return

    msg = "**Marcador de poder**\n"
    for i, row in enumerate(rows, start=1):
        location = row["current_kingdom"] or "ubicación desconocida"
        msg += (
            f"{i}. **{row['name']}** ({row['race']}) - "
            f"Nivel {row['level']} | Fama {row['total_fame']} | "
            f"Victorias {row['wins']} | {location}\n"
        )
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
async def comerciar(ctx, *, datos: str):
    parts = [p.strip() for p in datos.split("|")]
    if len(parts) != 3:
        await ctx.send("Formato: `!comerciar personaje|reino destino|objeto`")
        return

    ok, message = await trade_item(parts[0], parts[1], parts[2])
    if not ok:
        await ctx.send(f"❌ {message}")
        return
    await ctx.send(f"✅ {message}\nFama +1 en {parts[1]}.")

@bot.command()
async def comercio(ctx):
    rows = await get_recent_trades(limit=10)
    if not rows:
        await ctx.send("No hay comercio registrado.")
        return

    msg = "**Comercio reciente:**\n"
    for row in rows:
        origin = row["origin_kingdom"] or "origen desconocido"
        msg += f"• Día {row['day']}: {row['character_name']} movió {row['item_name']} de {origin} a {row['destination_kingdom']}\n"
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
    for row in arcs:
        msg += f"• {row['name']}: {row['arc_name']} ({row['arc_progress']}%)\n"
    await send_split(ctx, msg)

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
async def encuesta(ctx, *, pregunta_opciones: str):
    parts = pregunta_opciones.split("|")
    if len(parts) < 3:
        await ctx.send("Formato: `!encuesta pregunta|opcion1|opcion2|...`")
        return

    question = parts[0].strip()
    options = [p.strip() for p in parts[1:] if p.strip()]
    if len(options) < 2:
        await ctx.send("Necesitas al menos 2 opciones.")
        return
    if len(options) > 5:
        await ctx.send("Máximo 5 opciones por encuesta.")
        return

    day = await get_current_day()
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    msg = f"📊 **ENCUESTA RÁPIDA (Día {day})**\n{question}\n"
    for i, opt in enumerate(options):
        msg += f"{emojis[i]} {opt}\n"

    poll = await ctx.send(msg)
    vote_id = await create_vote(
        day,
        question,
        options,
        source="quick",
        vote_type="quick",
        close_after_hours=1
    )
    await set_vote_message_id(vote_id, poll.id)

    for i in range(len(options)):
        await poll.add_reaction(emojis[i])

@bot.command()
@commands.has_permissions(administrator=True)
async def cerrar_votacion(ctx, vote_id: int, *, resultado: str):
    vote = await get_vote(vote_id)
    if not vote:
        await ctx.send("No encontré esa votación.")
        return

    options = decode_vote_options(vote["options"])
    if vote["vote_type"] == "ability" and not option_is_valid(resultado, options):
        await ctx.send("❌ Ese resultado no existe entre las opciones de la votación de habilidad.")
        return

    await close_vote(vote_id, resultado)
    ability_message = ""
    if vote["vote_type"] == "ability" and not is_non_choice_result(resultado):
        character_name = await apply_unlocked_ability(vote_id, resultado)
        if character_name:
            ability_message = f"\n✨ {character_name} desbloqueó: **{resultado}**"
    await ctx.send(f"✅ Votación {vote_id} cerrada.\nResultado: {resultado}{ability_message}")

@bot.command()
@commands.has_permissions(administrator=True)
async def consecuencia(ctx, vote_id: int, *, texto: str):
    ok = await record_consequence(vote_id, texto)
    if not ok:
        await ctx.send("No encontré esa votación cerrada.")
        return
    await ctx.send(f"✅ Consecuencia registrada para votación {vote_id}.")

@bot.command()
async def votaciones(ctx, estado: str = None):
    status = None
    if estado in ("abiertas", "open"):
        status = "open"
    elif estado in ("cerradas", "closed"):
        status = "closed"

    rows = await get_votes(status=status, limit=10)
    if not rows:
        await ctx.send("No hay votaciones para mostrar.")
        return

    msg = "**Votaciones recientes:**\n"
    for row in rows:
        result = row["result"] or "sin resultado"
        consequence = f" | Consecuencia: {row['consequence']}" if row["consequence"] else ""
        msg += f"• #{row['id']} [{row['status']}/{row['vote_type']}] Día {row['day']} - {row['question']} → {result}{consequence}\n"
    await send_split(ctx, msg)

@bot.command()
async def eventos(ctx):
    rows = await get_active_key_events(limit=15)
    if not rows:
        await ctx.send("No hay eventos clave activos registrados.")
        return

    msg = "**Eventos clave activos:**\n"
    for row in rows:
        msg += f"• Día {row['day']} [{row['event_type']}] {row['title'] or 'Evento'}: {row['description']}\n"
    await send_split(ctx, msg)

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
    try:
        await reset_world_progress()
    except Exception as exc:
        await ctx.send(f"❌ No pude resetear el mundo: {exc}")
        return

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
@commands.has_permissions(administrator=True)
async def exportar_novela(ctx):
    from webnovel_exporter import export_web_novel
    path = await export_web_novel()
    await ctx.send(
        content="📚 **Web novel exportada**",
        file=discord.File(path)
    )

@bot.command()
async def generar_dia(ctx):
    channel = bot.get_channel(CHANNEL_ID)
    closed_votes = await close_pending_votes_for_manual_generation(channel)
    if closed_votes:
        closed_message = "🧪 **Votos abiertos cerrados antes de generar el día:**\n" + "\n".join(closed_votes)
        await send_split(ctx, closed_message)
        if channel and ctx.channel.id != CHANNEL_ID:
            for part in split_message(closed_message):
                await channel.send(part)

    clean_text, display_text, title, level_ups = await generate_next_day()

    # Enviar historia (maneja +2000 chars)
    await send_long_message(CHANNEL_ID, f"**{title}**\n{display_text}")

    # Obtener día actual (ya incrementado)
    day = await get_current_day()

    # Exportar a PDF
    from pdf_exporter import export_day_to_pdf
    pdf_path = export_day_to_pdf(day, title, clean_text)

    # Enviar PDF y borrar archivo temporal local.
    try:
        await ctx.send(
            content=f"📄 **Archivo del Día {day}**",
            file=discord.File(pdf_path)
        )
    finally:
        remove_file_safely(pdf_path)

    if channel:
        await publish_critical_decision(channel, day, clean_text)
        await publish_ability_votes(channel, day, level_ups)
        await publish_quote_of_day(channel, day)


bot.run(TOKEN)

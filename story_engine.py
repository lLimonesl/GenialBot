# story_engine.py
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from database import (
    get_world_state,
    get_full_characters,
    apply_level_ups,
    get_active_arcs,
    get_closed_votes,
    save_day,
    save_quotes,
    apply_inventory_changes,
    update_locations,
    apply_reputation_changes,
    create_character_arc,
    update_arc_progress,
    upsert_npcs,
    mark_npcs_inactive,
    save_battles,
    get_inventory_for_prompt,
    get_npcs,
    record_narrative_memory,
    get_narrative_memory,
    get_recent_full_days,
    get_all_days,
    get_active_key_events,
    add_key_event,
    get_vote_consequences,
    get_season_context,
    sync_world_season,
    get_character_by_name,
    get_recent_trades
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

METADATA_TAGS = (
    "WEATHER",
    "QUOTE",
    "ITEM_GAIN",
    "ITEM_LOSE",
    "LOCATION",
    "FAME",
    "NEW_ARC",
    "ARC_PROGRESS",
    "NPC_APPEAR",
    "NPC_DISAPPEAR",
    "BATTLE",
    "LEVEL_UP",
    "KEY_EVENT",
    "SEASON"
)
METADATA_LINE_RE = re.compile(
    rf"^\s*(?:[-*>`]+\s*)?\[({'|'.join(METADATA_TAGS)})\]\s*(.*)$"
)

async def generate_next_day():
    current_day, rules = await get_world_state()
    characters = await get_full_characters()
    arcs = await get_active_arcs()
    votes = await get_closed_votes()
    inventory = await get_inventory_for_prompt()
    npcs = await get_npcs()
    narrative_context = await build_narrative_context()
    key_events = await get_active_key_events()
    consequences = await get_vote_consequences(limit=5)
    season = await get_season_context()
    trades = await get_recent_trades(limit=5)

    char_text = "\n".join(
        f"""
- {c['name']} ({c['race']})
  Nivel actual: {c['level']}
  Arma: {c['weapon']}
  Amuleto: {c['amulet']}
  Mascota: {c['pet']}
  Habilidades: {c['abilities']}
  Pasivas: {c['passives']}
  Movimiento final: {c['final_move']}
""".strip()
        for c in characters
    )

    arc_text = "\n".join(
        f"- {a['name']}: {a['arc_name']} (progreso {a['arc_progress']}%)"
        for a in arcs
    )

    inventory_text = "\n".join(
        f"- {i['name']}: {i['item_name']} ({i['item_type']}) x{i['quantity']} - {i['item_description']}"
        for i in inventory
    ) or "Sin inventario adicional registrado."

    npc_text = "\n".join(
        f"- {n['name']} ({n['race'] or 'raza desconocida'}): {n['role'] or 'rol desconocido'} en {n['kingdom'] or 'ubicación desconocida'} - {n['description'] or ''}"
        for n in npcs
    ) or "Sin NPCs activos registrados."

    vote_text = "\n".join(
        f"- {v['question']} → {v['result']}" + (f" | Consecuencia: {v['consequence']}" if v['consequence'] else "")
        for v in votes
    ) or "Sin decisiones cerradas relevantes."

    key_event_text = "\n".join(
        f"- Día {e['day']} [{e['event_type']}] {e['title'] or 'Evento'}: {e['description']}"
        for e in key_events
    ) or "Sin eventos clave activos registrados."

    consequence_text = "\n".join(
        f"- Día {c['day']} | {c['question']} → {c['result']}: {c['consequence']}"
        for c in consequences
    ) or "Sin consecuencias registradas."

    season_text = f"{season['season']} (día {season['season_day']} de 30). {season['description']}"
    trade_text = "\n".join(
        f"- Día {t['day']}: {t['character_name']} comerció {t['item_name']} hacia {t['destination_kingdom']}"
        for t in trades
    ) or "Sin comercio reciente registrado."

    prompt = f"""
Eres el narrador de una historia isekai seria y coherente.

REGLAS DEL MUNDO:
{rules}

ESTACIÓN Y CLIMA PERSISTENTE:
{season_text}

HISTORIA ANTERIOR:
{narrative_context}

EVENTOS CLAVE ACTIVOS:
{key_event_text}

CONSECUENCIAS VISIBLES DE VOTACIONES:
{consequence_text}

COMERCIO RECIENTE ENTRE REINOS:
{trade_text}

REGLAS DE PROGRESIÓN:
- NO asignes niveles directamente.
- Cuando un personaje progresa, usa el formato exacto:
  [LEVEL_UP] Nombre +X niveles

REGLAS DE PODER:
- Los personajes SOLO pueden usar habilidades listadas.
- Las pasivas siempre están activas.
- Los límites y restricciones deben respetarse.
- No inventes nuevos poderes.
- Los movimientos finales solo pueden usarse en situaciones extremas.

PERSONAJES VIVOS:
{char_text}

ARCOS ACTIVOS:
{arc_text}

INVENTARIO ACTUAL:
{inventory_text}

NPCS ACTIVOS:
{npc_text}

DECISIONES DEL PUBLICO:
{vote_text}

Narrador omnisciente.

Escribe el Día {current_day + 1}.
No repitas eventos.
Las consecuencias son permanentes.

FORMATO DE METADATOS:
Si ocurre algo relevante, añade al final del texto líneas con estos formatos exactos.
No uses estos tags dentro de la narración normal.
- Si un personaje obtiene, compra, encuentra, fabrica, equipa o pierde un objeto relevante, DEBES registrar el cambio con [ITEM_GAIN] o [ITEM_LOSE].
- No inventes recompensas sin causa narrativa; solo registra objetos cuando realmente ocurran en la historia.
- [WEATHER] clima del día
- [QUOTE] Personaje: "frase memorable"
- [ITEM_GAIN] Personaje|Objeto|Tipo|Descripción
- [ITEM_LOSE] Personaje|Objeto
- [LOCATION] Personaje|Reino o ubicación
- [FAME] Personaje|Reino|+/-cantidad|motivo breve
- [NEW_ARC] Personaje|Nombre del arco|Objetivo
- [ARC_PROGRESS] Personaje|Nombre del arco|+cantidad
- [NPC_APPEAR] Nombre|Raza|Rol|Reino o ubicación|Descripción
- [NPC_DISAPPEAR] Nombre
- [BATTLE] participantes separados por coma|enemigos separados por coma|resultado|resumen breve
- [KEY_EVENT] tipo|título|descripción
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    text = response.choices[0].message.content
    metadata = extract_metadata(text)
    clean_text = strip_metadata_tags(text)

    level_ups = extract_level_ups(text)
    await apply_level_ups(level_ups)

    summary = build_summary(clean_text)
    new_day = await save_day(
        f"Día {current_day + 1}",
        clean_text,
        summary,
        metadata["weather"]
    )

    await save_quotes(new_day, metadata["quotes"])
    await apply_inventory_changes(metadata["item_gains"], metadata["item_losses"], new_day)
    await update_locations(metadata["locations"])
    await apply_reputation_changes(metadata["reputation"])
    await upsert_npcs(metadata["npcs_appear"], new_day)
    await mark_npcs_inactive(metadata["npcs_disappear"], new_day)
    await save_battles(new_day, metadata["battles"])
    await record_narrative_memory(new_day, "daily", summary)
    await sync_world_season(new_day)

    if new_day % 7 == 0:
        weekly_summary = await compress_week(new_day)
        await record_narrative_memory(new_day, "weekly", weekly_summary)

    if new_day % 28 == 0:
        compressed_summary = await compress_month(new_day)
        await record_narrative_memory(new_day, "compressed", compressed_summary)

    for event_type, title, description in metadata["key_events"]:
        await add_key_event(new_day, event_type, title, description)

    for character_name, arc_name, arc_goal in metadata["new_arcs"]:
        await create_character_arc(character_name, arc_name, arc_goal)

    for character_name, arc_name, amount in metadata["arc_progress"]:
        await update_arc_progress(character_name, arc_name, amount)

    display_text = append_metadata_summary(clean_text, metadata)
    return clean_text, display_text, f"Día {new_day}", level_ups

async def build_narrative_context():
    memory = await get_narrative_memory()
    recent_days = await get_recent_full_days(limit=3)

    if not memory:
        all_days = await get_all_days()
        recent_numbers = {d["day"] for d in recent_days}
        older_summaries = [d for d in all_days if d["day"] not in recent_numbers]
        sections = []
        if older_summaries:
            sections.append("RESÚMENES HISTÓRICOS EXISTENTES:\n" + "\n".join(
                f"- Día {d['day']}: {d['summary'] or ''}"
                for d in older_summaries
            ))
        if recent_days:
            ordered_days = list(reversed(recent_days))
            sections.append("ÚLTIMOS DÍAS COMPLETOS:\n" + "\n\n".join(
                f"Día {d['day']} - {d['title'] or 'Sin título'}\nClima: {d['weather'] or 'No registrado'}\n{d['full_text'] or d['summary'] or ''}"
                for d in ordered_days
            ))
        return "\n\n".join(sections) if sections else "Aún no hay historia previa registrada."

    compressed = [m for m in memory if m["summary_type"] == "compressed"]
    max_compressed_day = max([m["day"] for m in compressed], default=0)
    weekly = [m for m in memory if m["summary_type"] == "weekly" and m["day"] > max_compressed_day]

    sections = []
    if compressed:
        sections.append("RESÚMENES COMPRIMIDOS DE LA HISTORIA:\n" + "\n".join(
            f"- Hasta día {m['day']}: {m['content']}" for m in compressed
        ))
    if weekly:
        sections.append("RESÚMENES SEMANALES RECIENTES:\n" + "\n".join(
            f"- Semana hasta día {m['day']}: {m['content']}" for m in weekly
        ))
    if recent_days:
        ordered_days = list(reversed(recent_days))
        sections.append("ÚLTIMOS DÍAS COMPLETOS:\n" + "\n\n".join(
            f"Día {d['day']} - {d['title'] or 'Sin título'}\nClima: {d['weather'] or 'No registrado'}\n{d['full_text'] or d['summary'] or ''}"
            for d in ordered_days
        ))

    return "\n\n".join(sections) if sections else "Aún no hay historia previa registrada."

async def compress_week(day: int):
    memory = await get_narrative_memory()
    start = day - 6
    daily = [m for m in memory if m["summary_type"] == "daily" and start <= m["day"] <= day]
    content = "\n".join(f"Día {m['day']}: {m['content']}" for m in daily)
    if not content:
        return "Sin eventos suficientes para resumir esta semana."
    return await summarize_memory(content, "Resume esta semana de la historia en 300-500 palabras. Conserva eventos, consecuencias, combates, cambios de estado y giros importantes.")

async def compress_month(day: int):
    memory = await get_narrative_memory()
    start = day - 27
    weekly = [m for m in memory if m["summary_type"] == "weekly" and start <= m["day"] <= day]
    content = "\n".join(f"Hasta día {m['day']}: {m['content']}" for m in weekly)
    if not content:
        return "Sin resúmenes semanales suficientes para compresión mensual."
    return await summarize_memory(content, "Comprime estos resúmenes semanales en una memoria mensual de 400-600 palabras. No pierdas muertes, consecuencias, cambios de mundo ni progreso de personajes.")

async def summarize_memory(content: str, instruction: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"{instruction}\n\nCONTENIDO:\n{content}"}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

async def suggest_abilities_for_level_up(character_name: str):
    character = await get_character_by_name(character_name)
    if not character:
        return []
    prompt = f"""
Sugiere exactamente 3 habilidades desbloqueables para este personaje.
Deben ser coherentes con su raza, nivel, habilidades actuales, pasivas y estilo.
No contradigas sus limitaciones ni inventes poderes excesivos.

Personaje: {character['name']}
Raza: {character['race']}
Nivel: {character['level']}
Habilidades actuales: {character['abilities']}
Pasivas: {character['passives']}
Arma: {character['weapon']}
Movimiento final: {character['final_move']}

Responde solo en JSON: {{"abilities": ["habilidad 1", "habilidad 2", "habilidad 3"]}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    try:
        import json
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`").replace("json\n", "", 1).strip()
        data = json.loads(content)
        return [a for a in data.get("abilities", []) if isinstance(a, str)][:3]
    except Exception:
        return []

async def detect_critical_decision(text: str):
    """
    Devuelve None si no hay punto crítico,
    o un dict con pregunta y opciones si sí lo hay.
    """
    prompt = f"""
Analiza el siguiente texto narrativo.

TEXTO:
{text}

Pregunta:
¿Existe una decisión crítica que deba ser tomada por el público?

Reglas:
- Solo responde SI o NO.
- Si NO, responde exactamente: NO
- Si SI, responde en JSON con este formato:

{{
  "question": "...",
  "options": ["opción 1", "opción 2", "opción 3"]
}}

No inventes decisiones irrelevantes.
No propongas decisiones que contradigan reglas canónicas.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    content = response.choices[0].message.content.strip()

    if content == "NO":
        return None

    try:
        import json
        return json.loads(content)
    except Exception:
        return None

def extract_level_ups(text: str):
    """
    Detecta subidas de nivel en el texto.
    Formato esperado:
    [LEVEL_UP] Nombre +X
    """
    pattern = r"\[LEVEL_UP\]\s*(\w+)\s*\+(\d+)"
    matches = re.findall(pattern, text)

    results = []
    for name, amount in matches:
        results.append((name, int(amount)))

    return results

def build_summary(text: str, limit=700):
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rsplit(" ", 1)[0] + "..."

def strip_metadata_tags(text: str):
    clean_lines = []
    for line in text.splitlines():
        if METADATA_LINE_RE.match(line):
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()

def append_metadata_summary(text: str, metadata: dict):
    sections = []

    if metadata["weather"]:
        sections.append(f"☀️ **Clima:** {metadata['weather']}")

    if metadata["locations"]:
        lines = [f"• **{name}:** {location}" for name, location in metadata["locations"]]
        sections.append("🗺️ **Ubicaciones actualizadas**\n" + "\n".join(lines))

    if metadata["new_arcs"]:
        lines = [f"• **{name}:** {arc} - {goal}" for name, arc, goal in metadata["new_arcs"]]
        sections.append("📜 **Nuevos arcos**\n" + "\n".join(lines))

    if metadata["arc_progress"]:
        lines = [f"• **{name}:** {arc} +{amount}%" for name, arc, amount in metadata["arc_progress"]]
        sections.append("📈 **Progreso de arcos**\n" + "\n".join(lines))

    if metadata["item_gains"]:
        lines = [f"• **{name}:** obtuvo {item} ({item_type})" for name, item, item_type, _ in metadata["item_gains"]]
        sections.append("🎒 **Objetos obtenidos**\n" + "\n".join(lines))

    if metadata["item_losses"]:
        lines = [f"• **{name}:** perdió {item}" for name, item in metadata["item_losses"]]
        sections.append("🧺 **Objetos perdidos**\n" + "\n".join(lines))

    if metadata["reputation"]:
        lines = [f"• **{name}:** {kingdom} {amount:+d} - {notes}" for name, kingdom, amount, notes in metadata["reputation"]]
        sections.append("🏰 **Fama/Reputación**\n" + "\n".join(lines))

    if metadata["quotes"]:
        lines = [f"• **{name}:** \"{quote}\"" for name, quote in metadata["quotes"]]
        sections.append("💬 **Citas memorables**\n" + "\n".join(lines))

    if metadata["npcs_appear"]:
        lines = [f"• **{name}:** {role} en {kingdom}" for name, _, role, kingdom, _ in metadata["npcs_appear"]]
        sections.append("👥 **NPCs relevantes**\n" + "\n".join(lines))

    if metadata["battles"]:
        lines = [f"• **{outcome}:** {summary}" for _, _, outcome, summary in metadata["battles"]]
        sections.append("⚔️ **Combates registrados**\n" + "\n".join(lines))

    if not sections:
        return text

    return text + "\n\n━━━━━━━━━━━━━━━━━━━━\n📌 **Registro del día**\n" + "\n\n".join(sections)

def extract_metadata(text: str):
    metadata = {
        "weather": None,
        "quotes": [],
        "item_gains": [],
        "item_losses": [],
        "locations": [],
        "reputation": [],
        "new_arcs": [],
        "arc_progress": [],
        "npcs_appear": [],
        "npcs_disappear": [],
        "battles": [],
        "key_events": []
    }

    for raw_line in text.splitlines():
        match = METADATA_LINE_RE.match(raw_line)
        if not match:
            continue

        line = f"[{match.group(1)}] {match.group(2).strip()}"

        if line.startswith("[WEATHER]"):
            metadata["weather"] = line.replace("[WEATHER]", "", 1).strip()

        elif line.startswith("[QUOTE]"):
            payload = line.replace("[QUOTE]", "", 1).strip()
            if ":" in payload:
                character_name, quote = payload.split(":", 1)
                metadata["quotes"].append((character_name.strip(), quote.strip().strip('"')))

        elif line.startswith("[ITEM_GAIN]"):
            parts = split_payload(line, "[ITEM_GAIN]", 4)
            if parts:
                metadata["item_gains"].append(tuple(parts))

        elif line.startswith("[ITEM_LOSE]"):
            parts = split_payload(line, "[ITEM_LOSE]", 2)
            if parts:
                metadata["item_losses"].append(tuple(parts))

        elif line.startswith("[LOCATION]"):
            parts = split_payload(line, "[LOCATION]", 2)
            if parts:
                metadata["locations"].append(tuple(parts))

        elif line.startswith("[FAME]"):
            parts = split_payload(line, "[FAME]", 4)
            if parts:
                try:
                    amount = int(parts[2].replace("+", ""))
                except ValueError:
                    continue
                metadata["reputation"].append((parts[0], parts[1], amount, parts[3]))

        elif line.startswith("[NEW_ARC]"):
            parts = split_payload(line, "[NEW_ARC]", 3)
            if parts:
                metadata["new_arcs"].append(tuple(parts))

        elif line.startswith("[ARC_PROGRESS]"):
            parts = split_payload(line, "[ARC_PROGRESS]", 3)
            if parts:
                try:
                    amount = int(parts[2].replace("+", ""))
                except ValueError:
                    continue
                metadata["arc_progress"].append((parts[0], parts[1], amount))

        elif line.startswith("[NPC_APPEAR]"):
            parts = split_payload(line, "[NPC_APPEAR]", 5)
            if parts:
                metadata["npcs_appear"].append(tuple(parts))

        elif line.startswith("[NPC_DISAPPEAR]"):
            name = line.replace("[NPC_DISAPPEAR]", "", 1).strip()
            if name:
                metadata["npcs_disappear"].append(name)

        elif line.startswith("[BATTLE]"):
            parts = split_payload(line, "[BATTLE]", 4)
            if parts:
                participants = [p.strip() for p in parts[0].split(",") if p.strip()]
                enemies = [e.strip() for e in parts[1].split(",") if e.strip()]
                metadata["battles"].append((participants, enemies, parts[2], parts[3]))

        elif line.startswith("[KEY_EVENT]"):
            parts = split_payload(line, "[KEY_EVENT]", 3)
            if parts:
                metadata["key_events"].append(tuple(parts))

    return metadata

def split_payload(line, tag, expected_parts):
    payload = line.replace(tag, "", 1).strip()
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) != expected_parts or any(not p for p in parts):
        return None
    return parts

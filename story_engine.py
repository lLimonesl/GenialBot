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
    get_current_pov,
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
    get_npcs
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_next_day():
    current_day, rules = await get_world_state()
    characters = await get_full_characters()
    arcs = await get_active_arcs()
    votes = await get_closed_votes()
    pov = await get_current_pov()
    inventory = await get_inventory_for_prompt()
    npcs = await get_npcs()

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
        f"- {v['question']} → {v['result']}"
        for v in votes
    )

    pov_text = (
        f"POV actual: {pov}. Narración limitada a su percepción."
        if pov else
        "Narrador omnisciente."
    )

    prompt = f"""
Eres el narrador de una historia isekai seria y coherente.

REGLAS DEL MUNDO:
{rules}

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

{pov_text}

Escribe el Día {current_day + 1}.
No repitas eventos.
Las consecuencias son permanentes.

FORMATO DE METADATOS:
Si ocurre algo relevante, añade al final del texto líneas con estos formatos exactos.
No uses estos tags dentro de la narración normal.
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

    for character_name, arc_name, arc_goal in metadata["new_arcs"]:
        await create_character_arc(character_name, arc_name, arc_goal)

    for character_name, arc_name, amount in metadata["arc_progress"]:
        await update_arc_progress(character_name, arc_name, amount)

    return append_metadata_summary(clean_text, metadata), f"Día {new_day}"

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
    tag_pattern = re.compile(
        r"^\s*\[(WEATHER|QUOTE|ITEM_GAIN|ITEM_LOSE|LOCATION|FAME|NEW_ARC|ARC_PROGRESS|NPC_APPEAR|NPC_DISAPPEAR|BATTLE|LEVEL_UP)\].*$",
        re.MULTILINE
    )
    return tag_pattern.sub("", text).strip()

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
        "battles": []
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()

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

    return metadata

def split_payload(line, tag, expected_parts):
    payload = line.replace(tag, "", 1).strip()
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) != expected_parts or any(not p for p in parts):
        return None
    return parts

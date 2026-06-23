# story_engine.py
import os
import re
import json
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
    get_recent_trades,
    get_quotes,
    get_all_legends,
    upsert_legends,
    append_world_rule_change,
    record_character_progression
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
    "SEASON",
    "LEGEND"
)
METADATA_LINE_RE = re.compile(
    rf"^\s*(?:[-*>`]+\s*)?\[({'|'.join(METADATA_TAGS)})\]\s*(.*)$"
)
LEVEL_UP_RE = re.compile(r"^\s*(?:[-*>`]+\s*)?\[LEVEL_UP\]\s*(.+?)\s*\+(\d+)(?:\s+niveles?)?\s*$", re.IGNORECASE)

PROMPT_LEAK_HEADINGS = (
    "REGLAS DEL MUNDO:",
    "ESTACIÓN Y CLIMA PERSISTENTE:",
    "HISTORIA ANTERIOR:",
    "EVENTOS CLAVE ACTIVOS:",
    "CONSECUENCIAS VISIBLES DE VOTACIONES:",
    "COMERCIO RECIENTE ENTRE REINOS:",
    "REGLAS DE PROGRESIÓN:",
    "REGLAS DE PODER:",
    "PERSONAJES VIVOS:",
    "ARCOS ACTIVOS:",
    "INVENTARIO ACTUAL:",
    "NPCS ACTIVOS:",
    "DECISIONES DEL PUBLICO:",
    "FORMATO DE METADATOS:",
)

def parse_json_field(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

def format_prompt_value(value, indent=0):
    value = parse_json_field(value)
    prefix = "  " * indent
    if value is None or value == {} or value == []:
        return "No definido."
    if isinstance(value, dict):
        if {"name", "description"}.issubset(value.keys()):
            parts = [f"{value['name']}: {value['description']}"]
            if value.get("limits") and value["limits"] != "Sin limite adicional definido.":
                parts.append(f"Limites: {value['limits']}")
            if value.get("cost") and value["cost"] != "Sin coste adicional definido.":
                parts.append(f"Coste: {value['cost']}")
            if value.get("cooldown") and value["cooldown"] != "Sin enfriamiento definido.":
                parts.append(f"Enfriamiento/duracion: {value['cooldown']}")
            if value.get("requirement"):
                parts.append(f"Requisito: {value['requirement']}")
            if value.get("notes"):
                parts.append(f"Notas: {value['notes']}")
            return " | ".join(parts)
        lines = []
        for key, item in value.items():
            lines.append(f"{prefix}- {str(key).replace('_', ' ').title()}: {format_prompt_value(item, indent + 1)}")
        return "\n".join(lines)
    if isinstance(value, list):
        return "\n".join(f"{prefix}- {format_prompt_value(item, indent + 1)}" for item in value)
    if isinstance(value, bool):
        return "Si" if value else "No"
    return str(value)

def format_character_for_prompt(character):
    return f"""
- {character['name']} ({character['race']})
  Nivel actual: {character['level']}
  Arma: {character['weapon'] or 'N/A'}
  Amuleto: {character['amulet'] or 'N/A'}
  Mascota:
{format_prompt_value(character['pet'], 2)}
  Habilidades:
{format_prompt_value(character['abilities'], 2)}
  Pasivas:
{format_prompt_value(character['passives'], 2)}
  Movimiento final:
{format_prompt_value(character['final_move'], 2)}
""".strip()

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
    legends = await get_all_legends(active_only=True)
    recent_days = await get_recent_full_days(limit=5)
    recent_focus = extract_recent_character_focus(recent_days, characters)
    recent_quotes = await get_quotes(limit=12)
    recent_quote_text = "\n".join(
        f"- Día {q['day']} | {q['character_name']}: \"{q['quote']}\""
        for q in recent_quotes
    ) or "Sin citas recientes registradas."

    char_text = "\n\n".join(format_character_for_prompt(c) for c in characters)

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

    legend_text = "\n".join(
        f"- {l['name']} ({l['power_level'] or 'poder desconocido'}) en {l['kingdom'] or 'ubicación desconocida'} [{l['status']}]: {l['description'] or ''}"
        for l in legends
    ) or "Sin leyendas enemigas persistentes registradas."

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

LEYENDAS ENEMIGAS PERSISTENTES:
{legend_text}

REGLAS DE PROGRESIÓN:
- NO asignes niveles directamente.
- Cuando un personaje progresa, usa el formato exacto:
  [LEVEL_UP] Nombre +X niveles

REGLAS DE PODER:
- Los personajes SOLO pueden usar habilidades listadas.
- Las pasivas siempre están activas.
- Los límites y restricciones deben respetarse.
- No inventes nuevos poderes.
- Si usas enemigos legendarios recurrentes, reutiliza LEYENDAS ENEMIGAS PERSISTENTES antes de inventar uno nuevo.
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

FOCO NARRATIVO RECIENTE:
{recent_focus or 'Sin foco reciente detectado.'}

CITAS RECIENTES A EVITAR:
{recent_quote_text}

Narrador omnisciente.

Escribe el Día {current_day + 1}.
No repitas eventos.
Las consecuencias son permanentes.
Reparte el protagonismo entre 3 a 5 personajes vivos.
Evita centrar el día en personajes que ya dominaron el foco reciente, salvo que sea inevitable por una consecuencia directa.
Incluye al menos una escena breve de otro grupo o personaje secundario para mantener el mundo vivo.
Las citas memorables deben variar de personaje; evita asignarlas al mismo personaje dominante del foco reciente si otro personaje tuvo una escena fuerte.
No generes citas parecidas a CITAS RECIENTES A EVITAR.
Si el personaje con más foco reciente ya tiene varias citas recientes, prioriza una cita memorable de otro personaje.
No copies ni resumas las secciones de contexto del prompt.
No incluyas encabezados como PERSONAJES VIVOS, REGLAS DE PODER, INVENTARIO ACTUAL, NPCS ACTIVOS o DECISIONES DEL PUBLICO en la respuesta final.
La respuesta final debe contener solo la narración del día y, al final, los metadatos con tags si aplican.

FORMATO DE METADATOS:
Si ocurre algo relevante, añade al final del texto líneas con estos formatos exactos.
No uses estos tags dentro de la narración normal.
- Genera como máximo 2 líneas [QUOTE] por día, de personajes distintos.
- No uses [QUOTE] para frases genéricas; solo para una frase realmente memorable y diferente a citas recientes.
- Si un personaje obtiene, compra, encuentra, fabrica, equipa o pierde un objeto relevante, DEBES registrar el cambio con [ITEM_GAIN] o [ITEM_LOSE].
- No inventes recompensas sin causa narrativa; solo registra objetos cuando realmente ocurran en la historia.
- Si narras una pelea, duelo, emboscada, combate, batalla o enfrentamiento físico/mágico, DEBES añadir una línea [BATTLE].
- Si un personaje aprende, mejora, supera un límite, gana experiencia importante o progresa por combate/entrenamiento, DEBES añadir [LEVEL_UP].
- Si una batalla cambia el equilibrio del mundo, deja heridos importantes, revela un enemigo o altera un reino, DEBES añadir también [KEY_EVENT].
- Si aparece, cambia o queda establecida una leyenda enemiga recurrente, DEBES añadir [LEGEND].
- Si un evento cambia una regla permanente del mundo, usa [KEY_EVENT] world_change|título|descripción.
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
- [LEVEL_UP] Personaje +1 niveles
- [KEY_EVENT] tipo|título|descripción
- [LEGEND] Nombre|Nivel/poder|Reino o ubicación|Estado|Descripción
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Eres un narrador. El contexto recibido es privado y nunca debe aparecer copiado en la respuesta."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    text = strip_prompt_leaks(response.choices[0].message.content)
    text = await validate_and_repair_consistency(text, rules, char_text, key_event_text, legend_text)
    metadata = extract_metadata(text)
    metadata["quotes"] = filter_memorable_quotes(metadata["quotes"], recent_quotes)
    clean_text = strip_metadata_tags(text)

    level_ups = extract_level_ups(text)
    metadata, level_ups = await repair_combat_metadata(clean_text, metadata, level_ups)
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
    await upsert_legends(metadata["legends"], new_day)
    await record_narrative_memory(new_day, "daily", summary)
    await sync_world_season(new_day)
    await record_character_progression(new_day)

    if new_day % 7 == 0:
        weekly_summary = await compress_week(new_day)
        await record_narrative_memory(new_day, "weekly", weekly_summary)

    if new_day % 28 == 0:
        compressed_summary = await compress_month(new_day)
        await record_narrative_memory(new_day, "compressed", compressed_summary)

    for event_type, title, description in metadata["key_events"]:
        await add_key_event(new_day, event_type, title, description)
        if event_type.strip().lower() == "world_change":
            await append_world_rule_change(new_day, title, description)

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

def extract_recent_character_focus(recent_days, characters):
    if not recent_days or not characters:
        return ""

    counts = {c["name"]: 0 for c in characters}
    for day in recent_days:
        text = f"{day['title'] or ''}\n{day['summary'] or ''}\n{day['full_text'] or ''}".lower()
        for name in counts:
            counts[name] += text.count(name.lower())

    focused = [
        f"{name} ({count} menciones recientes)"
        for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        if count > 0
    ][:5]
    return ", ".join(focused)

def quote_tokens(text):
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {word for word in cleaned.split() if len(word) > 3}

def quotes_are_similar(left, right):
    left_tokens = quote_tokens(left)
    right_tokens = quote_tokens(right)
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    return overlap / min(len(left_tokens), len(right_tokens)) >= 0.45

def filter_memorable_quotes(quotes, recent_quotes):
    if not quotes:
        return []

    recent_character_counts = {}
    for quote in recent_quotes[:12]:
        name = quote["character_name"]
        recent_character_counts[name] = recent_character_counts.get(name, 0) + 1

    filtered = []
    used_characters = set()
    recent_texts = [quote["quote"] for quote in recent_quotes[:16]]

    for character_name, quote in quotes:
        if character_name in used_characters:
            continue
        if recent_character_counts.get(character_name, 0) >= 2:
            continue
        if any(quotes_are_similar(quote, recent) for recent in recent_texts):
            continue

        filtered.append((character_name, quote))
        used_characters.add(character_name)
        if len(filtered) >= 2:
            break

    return filtered

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

async def validate_and_repair_consistency(text: str, rules: str, characters: str, key_events: str, legends: str):
    prompt = f"""
Revisa esta narración antes de publicarla.

REGLAS CANÓNICAS:
{rules}

PERSONAJES Y PODERES:
{characters}

EVENTOS ACTIVOS:
{key_events}

LEYENDAS PERSISTENTES:
{legends}

NARRACIÓN:
{text}

Tarea:
- Si la narración no contradice reglas, poderes, relaciones canónicas ni eventos activos, responde EXACTAMENTE: OK
- Si hay contradicciones, reescribe la narración completa corrigiéndolas.
- Conserva el mismo formato y conserva/metadatos válidos al final.
- No agregues explicaciones.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un verificador de continuidad. Responde OK o una narración corregida."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    content = response.choices[0].message.content.strip()
    if content.upper() == "OK":
        return text
    return strip_prompt_leaks(content)

async def repair_combat_metadata(text: str, metadata: dict, level_ups: list):
    combat_words = ("batalla", "combate", "duelo", "emboscada", "pelea", "enfrentamiento", "atac", "golpe", "herid")
    progress_words = ("aprend", "mejor", "progres", "super", "subió de nivel", "subio de nivel", "entren")
    lower_text = text.lower()

    needs_battle = not metadata["battles"] and any(word in lower_text for word in combat_words)
    needs_level = not level_ups and any(word in lower_text for word in progress_words)
    if not needs_battle and not needs_level:
        return metadata, level_ups

    prompt = f"""
Extrae metadatos faltantes de esta narración.

NARRACIÓN:
{text}

Reglas:
- Si hay batalla, pelea, duelo, emboscada o enfrentamiento, responde una línea [BATTLE].
- Si un personaje claramente aprende, mejora, supera un límite o sube de nivel, responde una línea [LEVEL_UP].
- No inventes eventos que no estén en la narración.
- Si no hay nada que extraer, responde NO.

Formatos exactos:
[BATTLE] participantes separados por coma|enemigos separados por coma|resultado|resumen breve
[LEVEL_UP] Personaje +1 niveles
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Responde solo con líneas de metadatos válidas o NO."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    content = response.choices[0].message.content.strip()
    if content.upper() == "NO":
        return metadata, level_ups

    repaired = extract_metadata(content)
    if not metadata["battles"]:
        metadata["battles"] = repaired["battles"]

    if not level_ups:
        level_ups = extract_level_ups(content)

    return metadata, level_ups

async def suggest_abilities_for_level_up(character_name: str):
    character = await get_character_by_name(character_name)
    if not character:
        return []
    prompt = f"""
Sugiere exactamente 3 habilidades desbloqueables para este personaje.
Cada opción debe tener nombre y una descripción breve de 1 frase.
Deben ser coherentes con su raza, nivel, habilidades actuales, pasivas y estilo.
No contradigas sus limitaciones ni inventes poderes excesivos.

Personaje: {character['name']}
Raza: {character['race']}
Nivel: {character['level']}
Habilidades actuales:
{format_prompt_value(character['abilities'])}
Pasivas:
{format_prompt_value(character['passives'])}
Arma: {character['weapon'] or 'N/A'}
Movimiento final:
{format_prompt_value(character['final_move'])}

Responde solo en JSON con este formato exacto:
{{"abilities": [{{"name": "Nombre", "description": "Descripción breve"}}, {{"name": "Nombre", "description": "Descripción breve"}}, {{"name": "Nombre", "description": "Descripción breve"}}]}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`").replace("json\n", "", 1).strip()
        data = json.loads(content)
        abilities = []
        for ability in data.get("abilities", []):
            if isinstance(ability, str):
                abilities.append(ability.strip())
                continue

            if not isinstance(ability, dict):
                continue

            name = str(ability.get("name") or "").strip()
            description = str(ability.get("description") or "").strip()
            if not name:
                continue

            abilities.append(f"{name}: {description}" if description else name)

        return abilities[:3]
    except Exception:
        return []

async def detect_critical_decision(text: str):
    """
    Devuelve None si no hay punto crítico,
    o un dict con pregunta y opciones si sí lo hay.
    """
    prompt = f"""
Analiza el siguiente texto narrativo de una historia interactiva.

TEXTO:
{text}

Pregunta:
¿Hay una decisión crítica de vida o muerte que deba tomar el público?

Reglas:
- Responde SI solo si uno o más personajes están en riesgo inmediato de morir, ser ejecutados, sacrificados, abandonados en una situación letal o sufrir una consecuencia irreversible equivalente.
- No crees votaciones por exploración, alianzas, negociación, entrenamiento, rutas, estrategia general o decisiones tácticas menores.
- La situación debe estar planteada al final del día o quedar claramente abierta para el siguiente día.
- Si no hay peligro mortal inmediato o consecuencia irreversible, responde exactamente: NO
- Si sí hay una decisión crítica, responde solo en JSON con este formato:

{{
  "question": "...",
  "options": ["opción 1", "opción 2", "opción 3"]
}}

No inventes decisiones irrelevantes.
No propongas decisiones que contradigan reglas canónicas.
Las opciones deben ser concretas, urgentes y relacionadas con salvar, sacrificar, arriesgar o abandonar a alguien.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Responde solo con JSON válido o NO."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.25
    )

    content = response.choices[0].message.content.strip()

    if content.upper() == "NO":
        return None

    try:
        import json
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
        json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if json_match:
            content = json_match.group(0)
        data = json.loads(content)
        question = str(data.get("question") or "").strip()
        options = [str(option).strip() for option in data.get("options", []) if str(option).strip()]
        if not question or len(options) < 2:
            return None
        return {"question": question, "options": options[:4]}
    except Exception:
        return None

async def suggest_vote_consequence(question: str, result: str):
    prompt = f"""
Genera una consecuencia narrativa breve y concreta para esta votación cerrada.

Pregunta: {question}
Resultado ganador: {result}

Reglas:
- La consecuencia debe ser visible en la historia futura.
- No contradigas reglas canónicas.
- No resumas la votación; describe el cambio narrativo causado.
- Máximo 2 frases.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35
    )
    return response.choices[0].message.content.strip()

def extract_level_ups(text: str):
    """
    Detecta subidas de nivel en el texto.
    Formato esperado:
    [LEVEL_UP] Nombre +X
    """
    results = []
    for line in text.splitlines():
        match = LEVEL_UP_RE.match(line)
        if not match:
            continue
        name, amount = match.groups()
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

def strip_prompt_leaks(text: str):
    lines = text.splitlines()

    for index, line in enumerate(lines):
        normalized = line.strip().upper()
        if normalized not in PROMPT_LEAK_HEADINGS:
            continue

        cut_index = index
        previous = index - 1
        while previous >= 0 and not lines[previous].strip():
            previous -= 1
        if previous >= 0 and lines[previous].strip().lower() in ("eventos clave:", "contexto:", "prompt:"):
            cut_index = previous

        return "\n".join(lines[:cut_index]).strip()

    return text.strip()

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

    if metadata["legends"]:
        lines = [f"• **{name}:** {level} en {kingdom} [{status}]" for name, level, kingdom, status, _ in metadata["legends"]]
        sections.append("👹 **Leyendas enemigas**\n" + "\n".join(lines))

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
        "key_events": [],
        "legends": []
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

        elif line.startswith("[LEGEND]"):
            parts = split_payload(line, "[LEGEND]", 5)
            if parts:
                metadata["legends"].append(tuple(parts))

    return metadata

def split_payload(line, tag, expected_parts):
    payload = line.replace(tag, "", 1).strip()
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) != expected_parts or any(not p for p in parts):
        return None
    return parts

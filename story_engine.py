# story_engine.py
import os
import re
from openai import OpenAI
from database import (
    get_world_state,
    increment_day,
    get_characters,
    get_full_characters,
    apply_level_ups,
    get_active_arcs,
    get_closed_votes,
    get_current_pov
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_next_day():
    current_day, rules = await get_world_state()
    characters = await get_full_characters()
    arcs = await get_active_arcs()
    votes = await get_closed_votes()
    pov = await get_current_pov()

    char_text = "\n".join(
        f"""
- {c['name']} ({c['race']})
  Nivel actual: {c.get('level', 'N/A')}
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

DECISIONES DEL PUBLICO:
{vote_text}

{pov_text}

Escribe el Día {current_day + 1}.
No repitas eventos.
Las consecuencias son permanentes.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    text = response.choices[0].message.content

    # 🔥 APLICAR LEVEL UPS AQUÍ
    level_ups = extract_level_ups(text)
    await apply_level_ups(level_ups)

    # Avanzar el día SOLO una vez
    await increment_day()

    return text, f"Día {current_day + 1}"

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
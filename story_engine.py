# story_engine.py
import os
from openai import OpenAI
from database import (
    get_world_state,
    increment_day,
    get_characters,
    get_active_arcs,
    get_closed_votes,
    get_current_pov
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_next_day():
    current_day, rules = await get_world_state()
    characters = await get_characters()
    arcs = await get_active_arcs()
    votes = await get_closed_votes()
    pov = await get_current_pov()

    char_text = "\n".join(
        f"- {c['name']} ({c['race']}, estado: {c['status']})"
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
    return text

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

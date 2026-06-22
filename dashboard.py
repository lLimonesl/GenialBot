import html

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import (
    get_active_arcs,
    get_active_key_events,
    get_all_characters_for_dashboard,
    get_all_days,
    get_battles,
    get_character_locations,
    get_character_stats,
    get_day_log,
    get_npcs,
    get_power_ranking,
    get_quotes,
    get_recent_trades,
)


app = FastAPI(title="GenialBot Dashboard")


def page(title, body):
    return HTMLResponse(f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #10141f; color: #edf2f7; }}
    header {{ padding: 24px; background: #171d2b; border-bottom: 1px solid #2b3348; }}
    main {{ max-width: 1000px; margin: 0 auto; padding: 24px; }}
    a {{ color: #8bd3ff; }}
    .card {{ background: #171d2b; border: 1px solid #2b3348; padding: 18px; margin: 14px 0; border-radius: 10px; }}
    .muted {{ color: #aab4c3; }}
    nav a {{ margin-right: 12px; }}
    pre {{ white-space: pre-wrap; font-family: inherit; line-height: 1.55; }}
  </style>
</head>
<body>
  <header>
    <h1>GenialBot</h1>
    <nav>
      <a href="/">Inicio</a><a href="/historia">Historia</a><a href="/personajes">Personajes</a><a href="/ranking">Ranking</a><a href="/mapa">Mapa</a><a href="/arcos">Arcos</a><a href="/npcs">NPCs</a><a href="/citas">Citas</a><a href="/eventos">Eventos</a><a href="/comercio">Comercio</a><a href="/novel">Novel</a>
    </nav>
  </header>
  <main>{body}</main>
</body>
</html>""")


@app.get("/", response_class=HTMLResponse)
async def home():
    days = await get_all_days()
    if not days:
        return page("GenialBot", "<p>No hay días generados todavía.</p>")
    latest = days[-1]
    latest_title = latest["title"] or f"Día {latest['day']}"
    body = f"<h2>{html.escape(latest_title)}</h2>"
    body += f"<p class='muted'>Día {latest['day']} | Clima: {html.escape(latest['weather'] or 'No registrado')}</p>"
    body += f"<div class='card'><pre>{html.escape(latest['full_text'] or latest['summary'] or '')}</pre></div>"
    return page("GenialBot", body)


@app.get("/historia", response_class=HTMLResponse)
async def history():
    days = await get_all_days()
    body = "<h2>Historia</h2>"
    for day in days:
        title = day["title"] or f"Día {day['day']}"
        body += f"<div class='card'><a href='/historia/{day['day']}'><strong>{html.escape(title)}</strong></a><p class='muted'>{html.escape(day['summary'] or '')}</p></div>"
    return page("Historia", body)


@app.get("/historia/{day}", response_class=HTMLResponse)
async def history_day(day: int):
    row = await get_day_log(day)
    if not row:
        return page("Día no encontrado", "<p>Día no encontrado.</p>")
    title = row["title"] or f"Día {day}"
    body = f"<h2>{html.escape(title)}</h2>"
    body += f"<p class='muted'>Clima: {html.escape(row['weather'] or 'No registrado')}</p>"
    body += f"<div class='card'><pre>{html.escape(row['full_text'] or row['summary'] or '')}</pre></div>"
    return page(title, body)


@app.get("/personajes", response_class=HTMLResponse)
async def characters():
    rows = await get_all_characters_for_dashboard()
    body = "<h2>Personajes</h2>"
    for row in rows:
        body += f"<div class='card'><a href='/personajes/{html.escape(row['name'])}'><strong>{html.escape(row['name'])}</strong></a> ({html.escape(row['race'])}) - Nivel {row['level']} - {html.escape(row['status'])}</div>"
    return page("Personajes", body)


@app.get("/personajes/{name}", response_class=HTMLResponse)
async def character_detail(name: str):
    data = await get_character_stats(name)
    if not data:
        return page("Personaje no encontrado", "<p>Personaje no encontrado.</p>")
    c = data["character"]
    body = f"<h2>{html.escape(c['name'])}</h2><div class='card'>"
    body += f"<p>Raza: {html.escape(c['race'])} | Estado: {html.escape(c['status'])} | Nivel: {c['level']}</p>"
    body += f"<p>Ubicación: {html.escape(c['current_kingdom'] or 'Desconocida')}</p>"
    body += f"<p>Combates registrados: {data['battle_count']}</p></div>"
    return page(c['name'], body)


@app.get("/mapa", response_class=HTMLResponse)
async def map_page():
    rows = await get_character_locations()
    body = "<h2>Mapa actual</h2>"
    for row in rows:
        body += f"<div class='card'>{html.escape(row['name'])} ({html.escape(row['race'])}): {html.escape(row['current_kingdom'] or 'Ubicación desconocida')}</div>"
    return page("Mapa", body)


@app.get("/arcos", response_class=HTMLResponse)
async def arcs_page():
    rows = await get_active_arcs()
    body = "<h2>Arcos activos</h2>"
    for row in rows:
        body += f"<div class='card'>{html.escape(row['name'])}: {html.escape(row['arc_name'])} ({row['arc_progress']}%)</div>"
    return page("Arcos", body)


@app.get("/npcs", response_class=HTMLResponse)
async def npcs_page():
    rows = await get_npcs(active_only=True)
    body = "<h2>NPCs activos</h2>"
    for row in rows:
        body += f"<div class='card'>{html.escape(row['name'])} - {html.escape(row['role'] or 'sin rol')} en {html.escape(row['kingdom'] or 'desconocido')}</div>"
    return page("NPCs", body)


@app.get("/citas", response_class=HTMLResponse)
async def quotes_page():
    rows = await get_quotes(limit=50)
    body = "<h2>Citas memorables</h2>"
    for row in rows:
        body += f"<div class='card'>Día {row['day']} - {html.escape(row['character_name'] or 'Desconocido')}: \"{html.escape(row['quote'])}\"</div>"
    return page("Citas", body)


@app.get("/ranking", response_class=HTMLResponse)
async def ranking_page():
    rows = await get_power_ranking()
    body = "<h2>Ranking</h2>"
    for i, row in enumerate(rows, start=1):
        body += f"<div class='card'>{i}. {html.escape(row['name'])} - Nivel {row['level']} | Fama {row['total_fame']} | Victorias {row['wins']}</div>"
    return page("Ranking", body)


@app.get("/eventos", response_class=HTMLResponse)
async def events_page():
    rows = await get_active_key_events(limit=50)
    body = "<h2>Eventos clave</h2>"
    for row in rows:
        body += f"<div class='card'>Día {row['day']} [{html.escape(row['event_type'])}] {html.escape(row['title'] or 'Evento')}: {html.escape(row['description'])}</div>"
    return page("Eventos", body)


@app.get("/comercio", response_class=HTMLResponse)
async def commerce_page():
    rows = await get_recent_trades(limit=50)
    body = "<h2>Comercio reciente</h2>"
    for row in rows:
        origin = row["origin_kingdom"] or "origen desconocido"
        body += f"<div class='card'>Día {row['day']}: {html.escape(row['character_name'] or 'Desconocido')} movió {html.escape(row['item_name'])} de {html.escape(origin)} a {html.escape(row['destination_kingdom'])}</div>"
    return page("Comercio", body)


@app.get("/novel", response_class=HTMLResponse)
async def novel_page():
    days = await get_all_days()
    body = "<h2>Web novel</h2>"
    for day in days:
        title = day["title"] or f"Día {day['day']}"
        body += f"<section class='card'><h3>{html.escape(title)}</h3><p class='muted'>Clima: {html.escape(day['weather'] or 'No registrado')}</p><pre>{html.escape(day['full_text'] or day['summary'] or '')}</pre></section>"
    return page("Web Novel", body)

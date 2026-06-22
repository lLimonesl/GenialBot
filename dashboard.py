import html
import json
from urllib.parse import quote

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
    get_votes,
)


app = FastAPI(title="GenialBot Dashboard")


def value_text(value):
    if value is None:
        return "N/A"
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return json.dumps(parsed, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def page(title, body):
    return HTMLResponse(f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #090b13;
      --panel: rgba(18, 24, 39, 0.82);
      --panel-strong: rgba(27, 36, 58, 0.9);
      --border: rgba(148, 163, 184, 0.18);
      --text: #f8fafc;
      --muted: #a8b3c7;
      --accent: #7dd3fc;
      --accent-strong: #c084fc;
      --gold: #facc15;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.36);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(125, 211, 252, 0.2), transparent 34rem),
        radial-gradient(circle at top right, rgba(192, 132, 252, 0.2), transparent 30rem),
        linear-gradient(135deg, #090b13 0%, #111827 48%, #050816 100%);
      color: var(--text);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
      background-size: 44px 44px;
      mask-image: linear-gradient(to bottom, rgba(0,0,0,0.7), transparent 75%);
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--border);
      background: rgba(9, 11, 19, 0.78);
      backdrop-filter: blur(18px);
    }}
    .hero {{ max-width: 1120px; margin: 0 auto; padding: 28px 24px 20px; }}
    .brand {{ display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }}
    .mark {{
      display: grid;
      width: 46px;
      height: 46px;
      place-items: center;
      border: 1px solid rgba(250, 204, 21, 0.35);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(250, 204, 21, 0.18), rgba(125, 211, 252, 0.16));
      box-shadow: 0 0 30px rgba(250, 204, 21, 0.12);
      font-size: 24px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 2px; font-size: clamp(1.7rem, 4vw, 2.8rem); letter-spacing: -0.04em; }}
    h2 {{ margin-bottom: 12px; font-size: clamp(1.55rem, 3vw, 2.35rem); letter-spacing: -0.035em; }}
    h3 {{ margin-bottom: 8px; color: #e2e8f0; }}
    .subtitle {{ margin: 0; color: var(--muted); }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 30px 24px 56px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ color: #bae6fd; }}
    nav {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    nav a {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      padding: 8px 13px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.72);
      color: #dbeafe;
      font-size: 0.92rem;
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
    }}
    nav a:hover {{
      transform: translateY(-1px);
      border-color: rgba(125, 211, 252, 0.5);
      background: rgba(14, 165, 233, 0.14);
    }}
    .card {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(145deg, var(--panel), rgba(15, 23, 42, 0.68));
      border: 1px solid var(--border);
      padding: 22px;
      margin: 16px 0;
      border-radius: 22px;
      box-shadow: var(--shadow);
    }}
    .card.compact {{ padding: 18px 20px; }}
    .card::after {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(120deg, rgba(255,255,255,0.09), transparent 30%);
      opacity: 0.42;
    }}
    .card > * {{ position: relative; z-index: 1; }}
    .card-link {{
      display: block;
      color: inherit;
      cursor: pointer;
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }}
    .card-link:hover {{
      transform: translateY(-2px);
      border-color: rgba(125, 211, 252, 0.52);
      background: linear-gradient(145deg, rgba(30, 41, 59, 0.94), rgba(14, 116, 144, 0.16));
    }}
    .card-link .title {{ color: #ffffff; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 18px; }}
    .grid .card {{ margin: 0; }}
    .title {{ display: block; margin-bottom: 7px; font-size: 1.06rem; font-weight: 800; letter-spacing: -0.01em; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 27px;
      padding: 4px 9px;
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.64);
      color: #cbd5e1;
      font-size: 0.84rem;
    }}
    .empty {{
      border: 1px dashed rgba(148, 163, 184, 0.28);
      background: rgba(15, 23, 42, 0.46);
      color: var(--muted);
      text-align: center;
    }}
    .quote {{ font-size: 1.04rem; line-height: 1.62; color: #eef6ff; }}
    .muted {{ color: var(--muted); }}
    pre {{
      white-space: pre-wrap;
      font-family: inherit;
      line-height: 1.7;
      margin: 0;
      color: #e5edf8;
    }}
    strong {{ color: #ffffff; }}
    @media (max-width: 720px) {{
      .hero {{ padding: 22px 16px 16px; }}
      main {{ padding: 22px 16px 42px; }}
      .brand {{ align-items: flex-start; }}
      nav {{ gap: 8px; overflow-x: auto; flex-wrap: nowrap; padding-bottom: 4px; }}
      nav a {{ white-space: nowrap; }}
      .card {{ padding: 18px; border-radius: 18px; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <div class="brand">
        <div class="mark">G</div>
        <div>
          <h1>GenialBot</h1>
          <p class="subtitle">Crónica viva del isekai, personajes, eventos y ranking de poder.</p>
        </div>
      </div>
      <nav>
        <a href="/">Inicio</a><a href="/historia">Historia</a><a href="/personajes">Personajes</a><a href="/ranking">Ranking</a><a href="/mapa">Mapa</a><a href="/arcos">Arcos</a><a href="/npcs">NPCs</a><a href="/citas">Citas</a><a href="/eventos">Eventos</a><a href="/votaciones">Votaciones</a><a href="/comercio">Comercio</a><a href="/novel">Novel</a>
      </nav>
    </div>
  </header>
  <main>{body}</main>
</body>
</html>""")


@app.get("/", response_class=HTMLResponse)
async def home():
    days = await get_all_days()
    if not days:
        return page("GenialBot", "<div class='card empty'>No hay días generados todavía.</div>")
    latest = days[-1]
    latest_title = latest["title"] or f"Día {latest['day']}"
    body = f"<h2>{html.escape(latest_title)}</h2>"
    body += f"<div class='meta'><span class='pill'>Día {latest['day']}</span><span class='pill'>Clima: {html.escape(latest['weather'] or 'No registrado')}</span></div>"
    body += f"<div class='card'><pre>{html.escape(latest['full_text'] or latest['summary'] or '')}</pre></div>"
    return page("GenialBot", body)


@app.get("/historia", response_class=HTMLResponse)
async def history():
    days = await get_all_days()
    body = "<h2>Historia</h2><div class='grid'>"
    for day in days:
        title = day["title"] or f"Día {day['day']}"
        body += f"<a class='card card-link' href='/historia/{day['day']}'><span class='title'>{html.escape(title)}</span><p class='muted'>{html.escape(day['summary'] or '')}</p><span class='pill'>Leer día {day['day']}</span></a>"
    body += "</div>"
    return page("Historia", body)


@app.get("/historia/{day}", response_class=HTMLResponse)
async def history_day(day: int):
    row = await get_day_log(day)
    if not row:
        return page("Día no encontrado", "<p>Día no encontrado.</p>")
    title = row["title"] or f"Día {day}"
    body = f"<h2>{html.escape(title)}</h2>"
    body += f"<div class='meta'><span class='pill'>Día {day}</span><span class='pill'>Clima: {html.escape(row['weather'] or 'No registrado')}</span></div>"
    body += f"<div class='card'><pre>{html.escape(row['full_text'] or row['summary'] or '')}</pre></div>"
    return page(title, body)


@app.get("/personajes", response_class=HTMLResponse)
async def characters():
    rows = await get_all_characters_for_dashboard()
    body = "<h2>Personajes</h2><div class='grid'>"
    for row in rows:
        name = html.escape(row["name"])
        race = html.escape(row["race"])
        status = html.escape(row["status"])
        path_name = quote(row["name"], safe="")
        body += f"<a class='card card-link compact' href='/personajes/{path_name}'><span class='title'>{name}</span><div class='meta'><span class='pill'>{race}</span><span class='pill'>Nivel {row['level']}</span><span class='pill'>{status}</span></div></a>"
    body += "</div>"
    return page("Personajes", body)


@app.get("/personajes/{name}", response_class=HTMLResponse)
async def character_detail(name: str):
    data = await get_character_stats(name)
    if not data:
        return page("Personaje no encontrado", "<p>Personaje no encontrado.</p>")
    c = data["character"]
    body = f"<h2>{html.escape(c['name'])}</h2><div class='card'>"
    body += f"<div class='meta'><span class='pill'>Raza: {html.escape(c['race'])}</span><span class='pill'>Estado: {html.escape(c['status'])}</span><span class='pill'>Nivel {c['level']}</span></div>"
    body += f"<p class='muted'>Estatus social</p><p>{html.escape(c['social_status'])}</p>"
    body += f"<p class='muted'>Ubicación actual</p><p>{html.escape(c['current_kingdom'] or 'Desconocida')}</p>"
    body += f"<p class='muted'>Arma</p><p>{html.escape(c['weapon'] or 'N/A')}</p>"
    body += f"<p class='muted'>Amuleto</p><p>{html.escape(c['amulet'] or 'N/A')}</p>"
    body += f"<p class='muted'>Mascota</p><pre>{html.escape(value_text(c['pet']))}</pre>"
    body += f"<p class='muted'>Habilidades</p><pre>{html.escape(value_text(c['abilities']))}</pre>"
    body += f"<p class='muted'>Pasivas</p><pre>{html.escape(value_text(c['passives']))}</pre>"
    body += f"<p class='muted'>Movimiento final</p><pre>{html.escape(value_text(c['final_move']))}</pre>"
    body += f"<p class='muted'>Combates registrados: {data['battle_count']}</p></div>"
    if data["arcs"]:
        body += "<h3>Arcos</h3><div class='grid'>"
        for arc in data["arcs"]:
            body += f"<div class='card compact'><span class='title'>{html.escape(arc['arc_name'])}</span><p class='muted'>{html.escape(arc['arc_goal'] or '')}</p><div class='meta'><span class='pill'>{html.escape(arc['arc_status'] or 'sin estado')}</span><span class='pill'>{arc['arc_progress']}%</span></div></div>"
        body += "</div>"
    if data["items"]:
        body += "<h3>Inventario</h3><div class='grid'>"
        for item in data["items"]:
            equipped = "equipado" if item["equipped"] else "guardado"
            body += f"<div class='card compact'><span class='title'>{html.escape(item['item_name'])}</span><p class='muted'>{html.escape(item['item_description'] or 'Sin descripción')}</p><div class='meta'><span class='pill'>x{item['quantity']}</span><span class='pill'>{html.escape(item['item_type'] or 'sin tipo')}</span><span class='pill'>{equipped}</span></div></div>"
        body += "</div>"
    if data["reputation"]:
        body += "<h3>Fama</h3><div class='grid'>"
        for rep in data["reputation"]:
            body += f"<div class='card compact'><span class='title'>{html.escape(rep['kingdom'])}</span><div class='meta'><span class='pill'>Fama {rep['fame_level']}</span></div><p class='muted'>{html.escape(rep['notes'] or '')}</p></div>"
        body += "</div>"
    return page(c['name'], body)


@app.get("/mapa", response_class=HTMLResponse)
async def map_page():
    rows = await get_character_locations()
    body = "<h2>Mapa actual</h2><div class='grid'>"
    for row in rows:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><div class='meta'><span class='pill'>{html.escape(row['race'])}</span><span class='pill'>{html.escape(row['current_kingdom'] or 'Ubicación desconocida')}</span></div></div>"
    body += "</div>"
    return page("Mapa", body)


@app.get("/arcos", response_class=HTMLResponse)
async def arcs_page():
    rows = await get_active_arcs()
    body = "<h2>Arcos activos</h2><div class='grid'>"
    for row in rows:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['arc_name'])}</span><p class='muted'>{html.escape(row['name'])}</p><span class='pill'>Progreso {row['arc_progress']}%</span></div>"
    body += "</div>"
    return page("Arcos", body)


@app.get("/npcs", response_class=HTMLResponse)
async def npcs_page():
    rows = await get_npcs(active_only=True)
    body = "<h2>NPCs activos</h2><div class='grid'>"
    for row in rows:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><div class='meta'><span class='pill'>{html.escape(row['role'] or 'sin rol')}</span><span class='pill'>{html.escape(row['kingdom'] or 'desconocido')}</span></div></div>"
    body += "</div>"
    return page("NPCs", body)


@app.get("/citas", response_class=HTMLResponse)
async def quotes_page():
    rows = await get_quotes(limit=50)
    body = "<h2>Citas memorables</h2>"
    for row in rows:
        body += f"<div class='card'><p class='quote'>\"{html.escape(row['quote'])}\"</p><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>{html.escape(row['character_name'] or 'Desconocido')}</span></div></div>"
    return page("Citas", body)


@app.get("/ranking", response_class=HTMLResponse)
async def ranking_page():
    rows = await get_power_ranking()
    body = "<h2>Ranking</h2><div class='grid'>"
    for i, row in enumerate(rows, start=1):
        medal = "Campeón" if i == 1 else f"Puesto {i}"
        body += f"<div class='card compact'><span class='title'>{i}. {html.escape(row['name'])}</span><div class='meta'><span class='pill'>{medal}</span><span class='pill'>Nivel {row['level']}</span><span class='pill'>Fama {row['total_fame']}</span><span class='pill'>Victorias {row['wins']}</span></div></div>"
    body += "</div>"
    return page("Ranking", body)


@app.get("/eventos", response_class=HTMLResponse)
async def events_page():
    rows = await get_active_key_events(limit=50)
    body = "<h2>Eventos clave</h2>"
    for row in rows:
        body += f"<div class='card'><span class='title'>{html.escape(row['title'] or 'Evento')}</span><p>{html.escape(row['description'])}</p><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>{html.escape(row['event_type'])}</span></div></div>"
    return page("Eventos", body)


@app.get("/votaciones", response_class=HTMLResponse)
async def votes_page():
    rows = await get_votes(limit=50)
    body = "<h2>Votaciones</h2>"
    for row in rows:
        result = row["result"] or "sin resultado"
        consequence = row["consequence"] or "sin consecuencia"
        body += f"<div class='card'><span class='title'>#{row['id']} - {html.escape(row['question'] or 'Votación')}</span><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>{html.escape(row['status'] or 'sin estado')}</span><span class='pill'>{html.escape(row['vote_type'] or 'critical')}</span><span class='pill'>Resultado: {html.escape(result)}</span></div><p class='muted'>Consecuencia: {html.escape(consequence)}</p></div>"
    return page("Votaciones", body)


@app.get("/comercio", response_class=HTMLResponse)
async def commerce_page():
    rows = await get_recent_trades(limit=50)
    body = "<h2>Comercio reciente</h2>"
    for row in rows:
        origin = row["origin_kingdom"] or "origen desconocido"
        body += f"<div class='card compact'><span class='title'>{html.escape(row['item_name'])}</span><p class='muted'>{html.escape(row['character_name'] or 'Desconocido')} movió este objeto.</p><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>Desde: {html.escape(origin)}</span><span class='pill'>Hacia: {html.escape(row['destination_kingdom'])}</span></div></div>"
    return page("Comercio", body)


@app.get("/novel", response_class=HTMLResponse)
async def novel_page():
    days = await get_all_days()
    body = "<h2>Web novel</h2>"
    for day in days:
        title = day["title"] or f"Día {day['day']}"
        body += f"<section class='card'><h3>{html.escape(title)}</h3><div class='meta'><span class='pill'>Día {day['day']}</span><span class='pill'>Clima: {html.escape(day['weather'] or 'No registrado')}</span></div><pre>{html.escape(day['full_text'] or day['summary'] or '')}</pre></section>"
    return page("Web Novel", body)

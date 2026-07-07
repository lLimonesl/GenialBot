import html
import json
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import (
    get_active_arcs,
    get_active_key_events,
    get_all_characters_for_dashboard,
    get_all_days,
    get_battle_detail,
    get_battles,
    get_character_locations,
    get_character_progression,
    get_character_stats,
    get_day_log,
    get_kingdom_detail,
    get_kingdoms_overview,
    get_npcs,
    get_power_ranking,
    get_quotes,
    get_recent_trades,
    get_timeline_events,
    get_votes,
)


app = FastAPI(title="GenialBot Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")


DISPLAY_KEY_LABELS = {
    "name": "Nombre o tipo",
    "description": "Descripcion",
    "limits": "Limites",
    "cost": "Coste",
    "cooldown": "Enfriamiento o duracion",
    "requirement": "Requisito",
    "notes": "Notas",
    "sex": "Genero",
    "gender": "Genero",
    "variant": "Variante",
    "revives": "Revive",
    "revive_days": "Dias para revivir",
    "habilidad": "Habilidad",
    "inmortal": "Inmortal",
}


def value_text(value):
    if value is None:
        return "N/A"
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return value_text(parsed)
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, dict):
        if not value:
            return "N/A"
        if set(value.keys()) == {"name"}:
            return f"Mascota/companero: {value_text(value['name'])}"
        if "name" in value:
            parts = [f"Mascota/companero: {value_text(value['name'])}"]
            if "description" in value:
                parts = [f"{value_text(value['name'])}: {value_text(value['description'])}"]
            for key, item in value.items():
                if key in {"name", "description"} or item in (None, "", [], {}):
                    continue
                if key == "limits" and item == "Sin limite adicional definido.":
                    continue
                if key == "cost" and item == "Sin coste adicional definido.":
                    continue
                if key == "cooldown" and item == "Sin enfriamiento definido.":
                    continue
                parts.append(f"{humanize_key(key)}: {value_text(item)}")
            return ", ".join(parts)
        return ", ".join(
            f"{humanize_key(key)}: {value_text(item)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        if not value:
            return "N/A"
        return ", ".join(value_text(item) for item in value)
    return str(value)


def humanize_key(key):
    return DISPLAY_KEY_LABELS.get(str(key), str(key).replace("_", " ").title())


def progress_width(value, reference, minimum=4):
    if reference <= 0:
        return minimum
    return max(minimum, min(100, int((abs(value or 0) / reference) * 100)))


def value_card(title, value):
    text = html.escape(value_text(value))
    return f"<div class='card compact trait-card group'><span class='label'>{html.escape(title)}</span><p>{text}</p></div>"


def info_card(title, value, accent=False):
    accent_class = " accent" if accent else ""
    return f"<div class='info-card{accent_class}'><span>{html.escape(title)}</span><strong>{html.escape(value_text(value))}</strong></div>"


def section_heading(title, subtitle=""):
    subtitle_html = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    return f"<div class='section-heading'><h3>{html.escape(title)}</h3>{subtitle_html}</div>"


def list_value(value):
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return parsed if isinstance(parsed, list) else [str(parsed)]
    return value if isinstance(value, list) else [str(value)]


def page(title, body):
    return HTMLResponse(f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="/static/dashboard.css">
</head>
<body>
  <div class="atmosphere" aria-hidden="true"><span></span><span></span><span></span></div>
  <header class="site-header">
    <a class="brand-island" href="/" aria-label="Ir al inicio de GenialBot">
      <span class="brand-mark"><span>G</span></span>
      <span><strong>GenialBot</strong><small>Archivo vivo del isekai</small></span>
    </a>
    <button class="menu-button" type="button" aria-label="Abrir navegación" aria-expanded="false" data-menu-button>
      <span></span><span></span>
    </button>
    <nav class="nav-shell" data-menu-panel>
      <a href="/">Inicio</a><a href="/historia">Historia</a><a href="/personajes">Personajes</a><a href="/ranking">Ranking</a><a href="/mapa">Mapa</a><a href="/reinos">Reinos</a><a href="/timeline">Timeline</a><a href="/progresion">Progresión</a><a href="/combates">Combates</a><a href="/arcos">Arcos</a><a href="/npcs">NPCs</a><a href="/citas">Citas</a><a href="/eventos">Eventos</a><a href="/votaciones">Votaciones</a><a href="/comercio">Comercio</a><a href="/novel">Novel</a>
    </nav>
  </header>
  <section class="hero-panel reveal">
    <p class="eyebrow">Observatorio narrativo</p>
    <h1>La crónica respira, pelea y recuerda.</h1>
    <p class="subtitle">Un archivo premium para leer el mundo, seguir personajes y entender cómo cambia el poder día a día.</p>
  </section>
  <main class="archive-shell"><div class="archive-core reveal">{body}</div></main>
  <script>
    const menuButton = document.querySelector('[data-menu-button]');
    const menuPanel = document.querySelector('[data-menu-panel]');
    menuButton?.addEventListener('click', () => {{
      const open = document.body.classList.toggle('menu-open');
      menuButton.setAttribute('aria-expanded', String(open));
    }});
    menuPanel?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {{
      document.body.classList.remove('menu-open');
      menuButton?.setAttribute('aria-expanded', 'false');
    }}));
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach((entry) => {{
        if (entry.isIntersecting) {{
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }}
      }});
    }}, {{ threshold: 0.12 }});
    document.querySelectorAll('.reveal, .card, .info-card, .profile-hero, .section-heading').forEach((node) => observer.observe(node));
  </script>
</body>
</html>""")


@app.get("/", response_class=HTMLResponse)
async def home():
    days = await get_all_days()
    if not days:
        return page("GenialBot", "<div class='card empty'>No hay días generados todavía.</div>")
    latest = days[-1]
    latest_title = latest["title"] or f"Día {latest['day']}"
    body = "<section class='p-5 sm:p-7'>"
    body += f"<p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-sky-300/80'>Último capítulo</p><h2>{html.escape(latest_title)}</h2>"
    body += f"<div class='meta'><span class='pill'>Día {latest['day']}</span><span class='pill'>Clima: {html.escape(latest['weather'] or 'No registrado')}</span></div>"
    body += f"<div class='card'><pre>{html.escape(latest['full_text'] or latest['summary'] or '')}</pre></div>"
    body += "</section>"
    return page("GenialBot", body)


@app.get("/historia", response_class=HTMLResponse)
async def history():
    days = await get_all_days()
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-violet-300/80'>Archivo narrativo</p><h2>Historia</h2><div class='grid'>"
    for day in days:
        title = day["title"] or f"Día {day['day']}"
        body += f"<a class='card card-link' href='/historia/{day['day']}'><span class='title'>{html.escape(title)}</span><p class='muted'>{html.escape(day['summary'] or '')}</p><span class='pill'>Leer día {day['day']}</span></a>"
    body += "</div></section>"
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
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-amber-300/80'>Roster</p><h2>Personajes</h2><div class='grid'>"
    for row in rows:
        name = html.escape(row["name"])
        race = html.escape(row["race"])
        status = html.escape(row["status"])
        path_name = quote(row["name"], safe="")
        body += f"<a class='card card-link compact' href='/personajes/{path_name}'><span class='title'>{name}</span><div class='meta'><span class='pill'>{race}</span><span class='pill'>Nivel {row['level']}</span><span class='pill'>{status}</span></div></a>"
    body += "</div></section>"
    return page("Personajes", body)


@app.get("/personajes/{name}", response_class=HTMLResponse)
async def character_detail(name: str):
    data = await get_character_stats(name)
    if not data:
        return page("Personaje no encontrado", "<p>Personaje no encontrado.</p>")
    c = data["character"]
    initial = html.escape((c["name"] or "?")[0].upper())
    body = "<section class='p-5 sm:p-7'><section class='profile-hero'>"
    body += f"<div class='avatar'>{initial}</div>"
    body += "<div>"
    body += f"<h2>{html.escape(c['name'])}</h2>"
    body += f"<p class='subtitle'>{html.escape(c['race'])} · {html.escape(c['social_status'])}</p>"
    body += f"<div class='meta'><span class='pill'>Estado: {html.escape(c['status'])}</span><span class='pill'>Nivel {c['level']}</span><span class='pill'>{html.escape(c['current_kingdom'] or 'Ubicación desconocida')}</span></div>"
    body += "</div></section>"
    body += "<div class='stat-grid'>"
    body += info_card("Arma", c["weapon"], accent=True)
    body += info_card("Amuleto", c["amulet"])
    body += info_card("Combates", str(data["battle_count"]))
    body += info_card("Ubicación", c["current_kingdom"] or "Desconocida")
    body += "</div>"
    body += section_heading("Ficha", "Rasgos centrales, poderes y límites conocidos del personaje.")
    body += "<div class='grid'>"
    body += value_card("Mascota", c["pet"])
    body += value_card("Habilidades", c["abilities"])
    body += value_card("Pasivas", c["passives"])
    body += value_card("Movimiento final", c["final_move"])
    body += "</div>"
    if data["arcs"]:
        body += section_heading("Arcos", "Progreso narrativo activo o completado.")
        body += "<div class='grid'>"
        for arc in data["arcs"]:
            body += f"<div class='card compact trait-card'><span class='label'>{html.escape(arc['arc_name'])}</span><p>{html.escape(arc['arc_goal'] or '')}</p><div class='meta'><span class='pill'>{html.escape(arc['arc_status'] or 'sin estado')}</span><span class='pill'>{arc['arc_progress']}%</span></div></div>"
        body += "</div>"
    if data["items"]:
        body += section_heading("Inventario", "Objetos registrados durante la historia.")
        body += "<div class='grid'>"
        for item in data["items"]:
            equipped = "equipado" if item["equipped"] else "guardado"
            body += f"<div class='card compact trait-card'><span class='label'>{html.escape(item['item_name'])}</span><p>{html.escape(item['item_description'] or 'Sin descripción')}</p><div class='meta'><span class='pill'>x{item['quantity']}</span><span class='pill'>{html.escape(item['item_type'] or 'sin tipo')}</span><span class='pill'>{equipped}</span></div></div>"
        body += "</div>"
    if data["reputation"]:
        body += section_heading("Fama", "Reputación acumulada por reino o facción.")
        body += "<div class='grid'>"
        for rep in data["reputation"]:
            body += f"<div class='card compact trait-card'><span class='label'>{html.escape(rep['kingdom'])}</span><div class='meta'><span class='pill'>Fama {rep['fame_level']}</span></div><p>{html.escape(rep['notes'] or 'Sin notas')}</p></div>"
        body += "</div>"
    body += "</section>"
    return page(c['name'], body)


@app.get("/mapa", response_class=HTMLResponse)
async def map_page():
    rows = await get_character_locations()
    body = "<h2>Mapa actual</h2><div class='grid'>"
    for row in rows:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><div class='meta'><span class='pill'>{html.escape(row['race'])}</span><span class='pill'>{html.escape(row['current_kingdom'] or 'Ubicación desconocida')}</span></div></div>"
    body += "</div>"
    return page("Mapa", body)


@app.get("/reinos", response_class=HTMLResponse)
async def kingdoms_page():
    rows = await get_kingdoms_overview()
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-sky-300/80'>Territorios</p><h2>Reinos y facciones</h2><div class='grid'>"
    for row in rows:
        kingdom = row["kingdom"]
        body += f"<a class='card card-link compact' href='/reinos/{quote(kingdom, safe='')}'><span class='title'>{html.escape(kingdom)}</span><span class='pill'>Ver detalle</span></a>"
    if not rows:
        body += "<div class='card empty'>No hay reinos con actividad registrada.</div>"
    body += "</div></section>"
    return page("Reinos", body)


@app.get("/reinos/{kingdom}", response_class=HTMLResponse)
async def kingdom_detail_page(kingdom: str):
    data = await get_kingdom_detail(kingdom)
    body = f"<section class='p-5 sm:p-7'><h2>{html.escape(kingdom)}</h2>"
    body += section_heading("Personajes", "Campeones o protagonistas ubicados actualmente aquí.")
    body += "<div class='grid'>"
    for row in data["characters"]:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><div class='meta'><span class='pill'>{html.escape(row['race'])}</span><span class='pill'>Nivel {row['level']}</span><span class='pill'>{html.escape(row['status'])}</span></div></div>"
    body += "</div>" if data["characters"] else "<div class='card empty'>Sin personajes registrados aquí.</div>"
    body += section_heading("NPCs", "Habitantes o figuras activas/inactivas del lugar.")
    body += "<div class='grid'>"
    for row in data["npcs"]:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><div class='meta'><span class='pill'>{html.escape(row['role'] or 'sin rol')}</span><span class='pill'>{html.escape(row['status'])}</span></div><p class='muted'>{html.escape(row['description'] or '')}</p></div>"
    body += "</div>" if data["npcs"] else "<div class='card empty'>Sin NPCs registrados.</div>"
    body += section_heading("Reputación", "Fama acumulada por personaje.")
    for row in data["reputation"]:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><span class='pill'>Fama {row['fame_level']}</span><p class='muted'>{html.escape(row['notes'] or '')}</p></div>"
    body += section_heading("Comercio", "Movimientos de objetos relacionados con este territorio.")
    for row in data["trades"]:
        origin = row["origin_kingdom"] or "origen desconocido"
        body += f"<div class='card compact'><span class='title'>{html.escape(row['item_name'])}</span><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>Desde {html.escape(origin)}</span><span class='pill'>Hacia {html.escape(row['destination_kingdom'])}</span></div></div>"
    body += section_heading("Eventos", "Eventos clave que mencionan este reino o facción.")
    for row in data["events"]:
        body += f"<div class='card'><span class='title'>{html.escape(row['title'] or 'Evento')}</span><p>{html.escape(row['description'])}</p><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>{html.escape(row['event_type'])}</span></div></div>"
    body += section_heading("Leyendas", "Enemigos persistentes asociados al lugar.")
    for row in data["legends"]:
        body += f"<div class='card compact'><span class='title'>{html.escape(row['name'])}</span><div class='meta'><span class='pill'>{html.escape(row['power_level'] or 'poder desconocido')}</span><span class='pill'>{html.escape(row['status'])}</span></div><p>{html.escape(row['description'] or '')}</p></div>"
    body += "</section>"
    return page(kingdom, body)


@app.get("/timeline", response_class=HTMLResponse)
async def timeline_page():
    rows = await get_timeline_events(limit=250)
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-violet-300/80'>Cronología</p><h2>Línea de tiempo</h2>"
    current_day = None
    for row in rows:
        if row["day"] != current_day:
            current_day = row["day"]
            body += f"<h3 class='mt-8'>Día {current_day}</h3>"
        body += f"<details class='card compact' open><summary><strong>{html.escape(row['title'] or row['event_type'])}</strong> <span class='pill'>{html.escape(row['event_type'])}</span></summary><p class='muted mt-3'>{html.escape(row['description'] or '')}</p></details>"
    body += "</section>"
    return page("Timeline", body)


@app.get("/progresion", response_class=HTMLResponse)
async def progression_page():
    rows = await get_character_progression()
    grouped = {}
    max_level = 1
    max_fame_abs = 1
    max_day = 0
    for row in rows:
        grouped.setdefault(row["character_name"], []).append(row)
        max_level = max(max_level, row["level"])
        max_fame_abs = max(max_fame_abs, abs(row["total_fame"] or 0))
        max_day = max(max_day, row["day"])
    level_reference = max(100, ((max_level + 9) // 10) * 10)
    fame_reference = max(50, ((max_fame_abs + 9) // 10) * 10)
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-emerald-300/80'>Crecimiento</p><h2>Progresión de personajes</h2>"
    if not grouped:
        body += "<div class='card empty'>La progresión empezará a registrarse desde el próximo día generado.</div></section>"
        return page("Progresión", body)
    body += "<div class='progress-overview'>"
    body += info_card("Personajes con progreso", str(len(grouped)), accent=True)
    body += info_card("Escala de nivel", f"0-{level_reference}")
    body += info_card("Escala de fama", f"±{fame_reference}")
    body += info_card("Último día registrado", f"Día {max_day}")
    body += "</div>"

    sorted_groups = sorted(
        grouped.items(),
        key=lambda item: (item[1][-1]["level"] or 0, item[1][-1]["total_fame"] or 0, item[0]),
        reverse=True,
    )
    for name, points in sorted_groups:
        recent_points = points[-20:]
        latest = points[-1]
        first_recent = recent_points[0]
        level_delta = latest["level"] - first_recent["level"]
        fame_delta = (latest["total_fame"] or 0) - (first_recent["total_fame"] or 0)
        level_width = progress_width(latest["level"], level_reference)
        fame_width = progress_width(latest["total_fame"], fame_reference)
        fame_tone = "negative" if (latest["total_fame"] or 0) < 0 else "positive"
        body += "<div class='card progress-card'>"
        body += "<div class='progress-head'>"
        body += f"<div><span class='title'>{html.escape(name)}</span><p class='muted'>Último registro: día {latest['day']}. Barras medidas contra una escala estable, no contra otros personajes.</p></div>"
        body += f"<span class='delta'>Nivel {level_delta:+d} · Fama {fame_delta:+d}</span>"
        body += "</div>"
        body += f"<div class='progress-row'><div class='progress-label'><span>Nivel actual</span><small>{latest['level']} / {level_reference}</small></div><div class='meter' title='Nivel {latest['level']} de {level_reference}'><div class='meter-fill level' style='width:{level_width}%'></div></div></div>"
        body += f"<div class='progress-row'><div class='progress-label'><span>Fama acumulada</span><small>{latest['total_fame']} / ±{fame_reference}</small></div><div class='meter' title='Fama {latest['total_fame']} contra referencia ±{fame_reference}'><div class='meter-fill fame {fame_tone}' style='width:{fame_width}%'></div></div></div>"
        body += "<div class='sparkline' aria-label='Tendencia de nivel de los últimos registros'>"
        for point in recent_points:
            spark_height = progress_width(point["level"], level_reference, minimum=8)
            body += f"<span class='spark' style='height:{spark_height}%' title='Día {point['day']}: nivel {point['level']}, fama {point['total_fame']}'></span>"
        body += "</div>"
        for point in recent_points[-6:]:
            point_level_width = progress_width(point["level"], level_reference)
            point_fame_width = progress_width(point["total_fame"], fame_reference)
            point_fame_tone = "negative" if (point["total_fame"] or 0) < 0 else "positive"
            body += "<div class='progress-point'>"
            body += f"<div class='meta'><span class='pill'>Día {point['day']}</span><span class='pill'>Nivel {point['level']}</span><span class='pill'>Fama {point['total_fame']}</span></div>"
            body += f"<div class='progress-row'><div class='progress-label'><span>Nivel</span><small>{point['level']} / {level_reference}</small></div><div class='meter'><div class='meter-fill level' style='width:{point_level_width}%'></div></div></div>"
            body += f"<div class='progress-row'><div class='progress-label'><span>Fama</span><small>{point['total_fame']} / ±{fame_reference}</small></div><div class='meter'><div class='meter-fill fame {point_fame_tone}' style='width:{point_fame_width}%'></div></div></div>"
            body += "</div>"
        body += "</div>"
    body += "</section>"
    return page("Progresión", body)


@app.get("/combates", response_class=HTMLResponse)
async def battles_page():
    rows = await get_battles(limit=100)
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-red-300/80'>Registro bélico</p><h2>Combates</h2><div class='grid'>"
    for row in rows:
        body += f"<a class='card card-link' href='/combates/{row['id']}'><span class='title'>{html.escape(row['outcome'] or 'Combate')}</span><p class='muted'>{html.escape(row['summary'] or '')}</p><span class='pill'>Día {row['day']}</span></a>"
    body += "</div></section>"
    return page("Combates", body)


@app.get("/combates/{battle_id}", response_class=HTMLResponse)
async def battle_detail_page(battle_id: int):
    row = await get_battle_detail(battle_id)
    if not row:
        return page("Combate no encontrado", "<p>Combate no encontrado.</p>")
    participants = list_value(row["participants"])
    enemies = list_value(row["enemies"])
    body = f"<section class='p-5 sm:p-7'><h2>{html.escape(row['outcome'] or 'Combate')}</h2><div class='meta'><span class='pill'>Día {row['day']}</span><span class='pill'>Combate #{row['id']}</span></div><div class='card'><p>{html.escape(row['summary'] or '')}</p></div>"
    body += section_heading("Participantes") + "<div class='grid'>"
    for name in participants:
        body += f"<a class='card card-link compact' href='/personajes/{quote(str(name), safe='')}'><span class='title'>{html.escape(str(name))}</span></a>"
    body += "</div>" + section_heading("Enemigos") + "<div class='grid'>"
    for name in enemies:
        body += f"<div class='card compact'><span class='title'>{html.escape(str(name))}</span></div>"
    body += "</div></section>"
    return page("Combate", body)


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
    body = "<section class='p-5 sm:p-7'><p class='mb-2 text-sm font-bold uppercase tracking-[0.25em] text-emerald-300/80'>Marcador</p><h2>Ranking</h2><div class='grid'>"
    for i, row in enumerate(rows, start=1):
        medal = "Campeón" if i == 1 else f"Puesto {i}"
        body += f"<div class='card compact'><span class='title'>{i}. {html.escape(row['name'])}</span><div class='meta'><span class='pill'>{medal}</span><span class='pill'>Nivel {row['level']}</span><span class='pill'>Fama {row['total_fame']}</span><span class='pill'>Victorias {row['wins']}</span></div></div>"
    body += "</div></section>"
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
